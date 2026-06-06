from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .engine import get_wellness_tips, get_meal_plan, get_wellness_journey_feed
from foods.models import DailyNutrition, MealLog
from foods.scoring import compute_gut_score, FoodItem, UserContext

# Food keywords used by both SMS and Telegram routing
FOOD_KEYWORDS = [
    "injera", "misir", "shiro", "tibs", "kitfo", "ayib", "ergo", "tej",
    "gomen", "fasolia", "doro", "ater", "kik", "teff", "buna", "abish",
]


# ── AI endpoints ──────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wellness_tips(request):
    # Cache per user for 10 minutes
    cache_key = f"tips_{request.user.id}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    # ... existing logic ...
    result = get_wellness_tips(...)
    result["kuriftu_tip"] = kuriftu_tip

    cache.set(cache_key, result, timeout=600)  # 10 minutes
    return Response(result)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wellness_journey_feed(request):
    # Cache per user for 10 minutes
    cache_key = f"feed_{request.user.id}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    # ... existing logic ...
    feed = get_wellness_journey_feed(...)
    result = {"feed": feed, "gut_score": gut_score, "weekly_avg": weekly_avg, "streak": streak}

    cache.set(cache_key, result, timeout=600)  # 10 minutes
    return Response(result)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_meal_plan(request):
    """POST /api/v1/ai/meal-plan/"""
    days = request.data.get("days", 7)
    user = request.user
    profile = getattr(user, "profile", None)

    family = [{
        "name":        profile.display_name or user.username if profile else user.username,
        "member_type": "adult",
        "diet_type":   getattr(profile, "diet_type", "omnivore"),
        "conditions":  _get_conditions(profile),
    }]
    for member in user.family_members.all():
        family.append({
            "name":        member.name,
            "member_type": member.member_type,
            "diet_type":   member.diet_type,
            "conditions":  _get_member_conditions(member),
        })

    result = get_meal_plan(family, days)
    return Response(result)



# ── SMS webhook (Africa's Talking) ────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def sms_webhook(request):
    """POST /api/v1/ai/sms/"""
    text = request.data.get("text", "").strip().lower()
    reply = _process_sms_text(text)
    from django.http import HttpResponse
    return HttpResponse(reply, content_type="text/plain")


# ── Telegram webhook ──────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def telegram_webhook(request):
    """
    POST /api/v1/ai/telegram/
    Telegram sends ALL updates here — both messages and callback_queries (button taps).
    """
    from .telegram_bot import handle_message, handle_callback

    try:
        update = request.data

        # ── Inline button tap ─────────────────────────────────────────────────
        if "callback_query" in update:
            cq = update["callback_query"]
            chat_id     = cq["message"]["chat"]["id"]
            callback_id = cq["id"]
            data        = cq.get("data", "")
            first_name  = cq.get("from", {}).get("first_name", "")
            handle_callback(chat_id, callback_id, data, first_name)

        # ── Text message ──────────────────────────────────────────────────────
        elif "message" in update:
            msg        = update["message"]
            chat_id    = msg["chat"]["id"]
            text       = msg.get("text", "").strip()
            first_name = msg.get("from", {}).get("first_name", "")

            if not text:
                return Response({"ok": True})   # ignore voice/photo/sticker etc.

            handle_message(chat_id, text, first_name)

    except Exception as e:
        # Never crash — Telegram will retry if we return non-200
        import logging
        logging.getLogger(__name__).error(f"Telegram webhook error: {e}")

    return Response({"ok": True})


# ── Shared SMS text processor (used by both SMS + Telegram fallback) ───────────

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
    from foods.models import EthiopianFood
    found = []
    for kw in FOOD_KEYWORDS:
        if kw in text:
            try:
                food = EthiopianFood.objects.filter(slug__icontains=kw).first()
                if food:
                    found.append(FoodItem(
                        slug=food.slug,
                        fiber_g=food.fiber_g,
                        protein_g=food.protein_g,
                        iron_mg=food.iron_mg,
                        fermentation_score=food.fermentation_score,
                        inflammatory_index=food.inflammatory_index,
                        prebiotic_score=food.prebiotic_score,
                    ))
            except Exception:
                pass

    if not found:
        return "Could not find those foods. Try: injera misir shiro ayib tibs"

    result = compute_gut_score(found)
    tip = result.alerts[0]["message"] if result.alerts else "Keep eating Ethiopian — your gut is well fed!"
    return (
        f"Well-Net Score: {result.gut_score}/100 — {result.label}\n\n"
        f"Fiber: {result.fiber_g}g | Fermentation: {result.fermentation_total}\n\n"
        f"Tip: {tip}\n\n"
        f"{result.kuriftu_tip}\n\n"
        f"Reply TIPS for more advice."
    )


# ── Management command helper: set webhook ────────────────────────────────────

def set_telegram_webhook(base_url: str) -> dict:
    """
    Call this once after deploying to register your webhook with Telegram.
    base_url example: "https://yourapp.up.railway.app"

    Usage from Django shell:
        from ai.views import set_telegram_webhook
        set_telegram_webhook("https://yourapp.up.railway.app")
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
    if getattr(profile, "is_pregnant", False):    conditions.append("pregnant")
    if getattr(profile, "has_diabetes", False):   conditions.append("diabetes")
    if getattr(profile, "has_anemia", False):     conditions.append("anemia")
    if getattr(profile, "has_hypertension", False): conditions.append("hypertension")
    if getattr(profile, "is_fasting_season", False): conditions.append("fasting")
    return conditions


def _get_member_conditions(member) -> list[str]:
    conditions = []
    if member.member_type == "pregnant": conditions.append("pregnant")
    if member.has_diabetes:              conditions.append("diabetes")
    if member.has_anemia:               conditions.append("anemia")
    return conditions
