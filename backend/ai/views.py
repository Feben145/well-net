"""
ai/views.py — AI Wellness Assistant endpoints

Every view here is wrapped so that a database hiccup or a missing
related object returns a clear JSON error (with a "detail" field
during DEBUG) instead of an opaque 500 with no body. This is what
was needed to actually see why /ai/tips/ and /ai/feed/ were failing
on Render.
"""
from datetime import date, timedelta
import logging
import traceback

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .engine import get_wellness_tips, get_meal_plan, get_wellness_journey_feed

logger = logging.getLogger(__name__)


def _error_response(e: Exception, where: str, status_code: int = 500):
    """Consistent error shape. Includes traceback only when DEBUG=True."""
    logger.error(f"Well-Net AI error in {where}: {e}\n{traceback.format_exc()}")
    body = {"error": f"Something went wrong in {where}."}
    if getattr(settings, "DEBUG", False):
        body["detail"] = str(e)
        body["traceback"] = traceback.format_exc().splitlines()[-6:]
    return Response(body, status=status_code)


# ── AI endpoints ──────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wellness_tips(request):
    """GET /api/v1/ai/tips/"""
    try:
        from foods.models import DailyNutrition, MealLog
    except Exception as e:
        return _error_response(e, "wellness_tips (foods import)")

    try:
        profile = getattr(request.user, "profile", None)

        gut_score = 0
        kuriftu_tip = ""
        try:
            today_nutrition = DailyNutrition.objects.get(user=request.user, date=date.today())
            gut_score = today_nutrition.gut_score
            kuriftu_tip = today_nutrition.kuriftu_tip
        except DailyNutrition.DoesNotExist:
            pass

        today_logs = MealLog.objects.filter(user=request.user, date=date.today())
        top_foods = []
        for log in today_logs:
            try:
                top_foods.extend([mf.food.slug for mf in log.meallogfood_set.all()])
            except Exception:
                continue

        profile_context = {
            "primary_goal":      getattr(profile, "primary_goal", "general"),
            "is_pregnant":       getattr(profile, "is_pregnant", False),
            "has_diabetes":      getattr(profile, "has_diabetes", False),
            "kuriftu_guest":     getattr(profile, "kuriftu_guest", False),
            "is_fasting_season": getattr(profile, "is_fasting_season", False),
        }

        latest_log = today_logs.order_by("-created_at").first()
        weakest = "fiber"
        if latest_log:
            dims = {
                "fiber":        (latest_log.fiber_g_total or 0) / 25,
                "fermentation": (latest_log.fermentation_total or 0) / 6,
                "inflammation": max(0, (4 - (latest_log.inflammatory_net or 0)) / 8),
                "protein":      (latest_log.protein_g_total or 0) / 50,
            }
            weakest = min(dims, key=dims.get)

        language = getattr(profile, "preferred_language", "en") if profile else "en"

        result = get_wellness_tips(gut_score, weakest, top_foods[:3], profile_context, language)
        result["kuriftu_tip"] = result.get("kuriftu_tip") or kuriftu_tip
        return Response(result)

    except Exception as e:
        return _error_response(e, "wellness_tips")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_meal_plan(request):
    """POST /api/v1/ai/meal-plan/  { days?: int }"""
    try:
        days = int(request.data.get("days", 7))
    except (TypeError, ValueError):
        days = 7

    try:
        user = request.user
        profile = getattr(user, "profile", None)

        family = [{
            "name":        (getattr(profile, "display_name", "") or user.username),
            "member_type": "adult",
            "diet_type":   getattr(profile, "diet_type", "omnivore"),
            "conditions":  _get_conditions(profile),
        }]

        try:
            for member in user.family_members.all():
                family.append({
                    "name":        member.name,
                    "member_type": member.member_type,
                    "diet_type":   member.diet_type,
                    "conditions":  _get_member_conditions(member),
                })
        except Exception as e:
            logger.warning(f"Well-Net AI: could not load family members — {e}")

        result = get_meal_plan(family, days)
        return Response(result)

    except Exception as e:
        return _error_response(e, "generate_meal_plan")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wellness_journey_feed(request):
    """GET /api/v1/ai/feed/"""
    try:
        from foods.models import DailyNutrition
    except Exception as e:
        return _error_response(e, "wellness_journey_feed (foods import)")

    try:
        user = request.user
        profile = getattr(user, "profile", None)

        today = date.today()
        seven_ago = today - timedelta(days=6)

        weekly = DailyNutrition.objects.filter(user=user, date__gte=seven_ago, date__lte=today)
        weekly_avg = round(sum(r.gut_score for r in weekly) / weekly.count(), 1) if weekly.exists() else 0

        gut_score = getattr(profile, "current_gut_score", 0) if profile else 0
        streak    = getattr(profile, "wellness_streak_days", 0) if profile else 0

        profile_dict = {
            "primary_goal":      getattr(profile, "primary_goal", "general"),
            "is_fasting_season": getattr(profile, "is_fasting_season", False),
            "kuriftu_guest":     getattr(profile, "kuriftu_guest", False),
        }

        feed = get_wellness_journey_feed(gut_score, weekly_avg, streak, profile_dict)
        return Response({"feed": feed, "gut_score": gut_score, "weekly_avg": weekly_avg, "streak": streak})

    except Exception as e:
        return _error_response(e, "wellness_journey_feed")


# ── SMS webhook (Africa's Talking) ────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def sms_webhook(request):
    """POST /api/v1/ai/sms/"""
    try:
        text = request.data.get("text", "").strip().lower()
        reply = _process_sms_text(text)
        from django.http import HttpResponse
        return HttpResponse(reply, content_type="text/plain")
    except Exception as e:
        logger.error(f"Well-Net SMS webhook error: {e}\n{traceback.format_exc()}")
        from django.http import HttpResponse
        return HttpResponse("Well-Net is temporarily unavailable. Please try again shortly.", content_type="text/plain")


# ── Telegram webhook ──────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def telegram_webhook(request):
    """POST /api/v1/ai/telegram/"""
    try:
        from .telegram_bot import handle_message, handle_callback

        update = request.data

        if "callback_query" in update:
            cq = update["callback_query"]
            chat_id     = cq["message"]["chat"]["id"]
            callback_id = cq["id"]
            data        = cq.get("data", "")
            first_name  = cq.get("from", {}).get("first_name", "")
            handle_callback(chat_id, callback_id, data, first_name)

        elif "message" in update:
            msg        = update["message"]
            chat_id    = msg["chat"]["id"]
            text       = msg.get("text", "").strip()
            first_name = msg.get("from", {}).get("first_name", "")
            if text:
                handle_message(chat_id, text, first_name)

    except Exception as e:
        logger.error(f"Well-Net Telegram webhook error: {e}\n{traceback.format_exc()}")

    return Response({"ok": True})


# ── Shared SMS text processor ──────────────────────────────────────────────────

FOOD_KEYWORDS = [
    "injera", "misir", "shiro", "tibs", "kitfo", "ayib", "ergo", "tej",
    "gomen", "fasolia", "doro", "ater", "kik", "teff", "buna", "abish",
]


def _process_sms_text(text: str) -> str:
    t = text.lower()
    if any(kw in t for kw in FOOD_KEYWORDS):
        return _score_from_text(t)
    if any(kw in t for kw in ["tip", "tips", "advice"]):
        return (
            "Well-Net Gut Tips:\n\n"
            "1. Injera daily — teff prebiotic powerhouse\n"
            "2. Misir wot 3x/week — GI=19\n"
            "3. Add ayib or ergo — natural probiotics\n\n"
            "Reply KURIFTU for resort wellness info."
        )
    if any(kw in t for kw in ["kuriftu", "resort", "spa"]):
        return (
            "Kuriftu x Well-Net:\n"
            "• Gut Health Passport on check-in\n"
            "• Yoga & sound healing sessions\n"
            "• Personalized menu scoring\n"
            "Book: kurifturesorts.com"
        )
    return (
        "Selam! I am Well-Net wellness AI.\n\n"
        "Text foods you ate: injera misir tej\n"
        "Or type: TIPS / KURIFTU / EXPERT / SCORE\n\n"
        "Well-Net"
    )


def _score_from_text(text: str) -> str:
    try:
        from foods.models import EthiopianFood
        from foods.scoring import compute_gut_score, FoodItem
    except Exception as e:
        logger.error(f"Well-Net SMS scoring import failed: {e}")
        return "Well-Net is temporarily unavailable. Please try again shortly."

    found = []
    for kw in FOOD_KEYWORDS:
        if kw in text:
            try:
                food = EthiopianFood.objects.filter(slug__icontains=kw).first()
                if food:
                    found.append(FoodItem(
                        slug=food.slug,
                        fiber_g=food.fiber_g or 0,
                        protein_g=food.protein_g or 0,
                        iron_mg=food.iron_mg or 0,
                        fermentation_score=food.fermentation_score or 0,
                        inflammatory_index=food.inflammatory_index or 0,
                        prebiotic_score=food.prebiotic_score or 0,
                    ))
            except Exception:
                continue

    if not found:
        return "Could not find those foods. Try: injera misir shiro ayib tibs"

    try:
        result = compute_gut_score(found)
    except Exception as e:
        logger.error(f"Well-Net SMS compute_gut_score failed: {e}")
        return "Could not calculate your score right now. Please try again."

    tip = result.alerts[0]["message"] if getattr(result, "alerts", None) else "Keep eating Ethiopian — your gut is well fed!"
    return (
        f"Well-Net Score: {result.gut_score}/100 — {result.label}\n\n"
        f"Fiber: {result.fiber_g}g | Fermentation: {result.fermentation_total}\n\n"
        f"Tip: {tip}\n\n"
        f"{getattr(result, 'kuriftu_tip', '')}\n\n"
        f"Reply TIPS for more advice."
    )


# ── Webhook registration helper ────────────────────────────────────────────────

def set_telegram_webhook(base_url: str) -> dict:
    """
    Usage from Django shell:
        from ai.views import set_telegram_webhook
        set_telegram_webhook("https://well-net-backend.onrender.com")
    """
    import requests as req
    token = settings.TELEGRAM_BOT_TOKEN
    webhook_url = f"{base_url}/api/v1/ai/telegram/"
    response = req.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={"url": webhook_url},
        timeout=10,
    )
    return response.json()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_conditions(profile) -> list[str]:
    if not profile:
        return []
    conditions = []
    if getattr(profile, "is_pregnant", False):       conditions.append("pregnant")
    if getattr(profile, "has_diabetes", False):      conditions.append("diabetes")
    if getattr(profile, "has_anemia", False):        conditions.append("anemia")
    if getattr(profile, "has_hypertension", False):  conditions.append("hypertension")
    if getattr(profile, "is_fasting_season", False): conditions.append("fasting")
    return conditions


def _get_member_conditions(member) -> list[str]:
    conditions = []
    if member.member_type == "pregnant": conditions.append("pregnant")
    if member.has_diabetes:              conditions.append("diabetes")
    if member.has_anemia:                conditions.append("anemia")
    return conditions