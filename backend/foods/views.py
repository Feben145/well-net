from datetime import date, timedelta
import re

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .models import EthiopianFood, MealLog, MealLogFood, DailyNutrition
from .serializers import (
    FoodSerializer, MealLogSerializer,
    MealLogCreateSerializer, DailyNutritionSerializer,
)
from .scoring import compute_gut_score, FoodItem, UserContext


# ── Food Database ─────────────────────────────────────────────────────────────

class FoodListView(generics.ListAPIView):
    """
    GET /api/v1/foods/
    All data sourced from EPHI 2025 PDF via parse_ephi_pdf command.
    """
    serializer_class    = FoodSerializer
    permission_classes  = [permissions.AllowAny]
    filter_backends     = [DjangoFilterBackend, SearchFilter]
    filterset_fields    = [
        "category",
        "fasting_safe",
        "pregnancy_safe",
        "diabetes_friendly",
        "planner_weekly_safe",
    ]
    search_fields       = ["name_en", "name_am", "display_name"]
    pagination_class    = None

    def get_queryset(self):
        return EthiopianFood.objects.filter(is_active=True)


class FoodDetailView(generics.RetrieveAPIView):
    """GET /api/v1/foods/<slug>/"""
    serializer_class   = FoodSerializer
    permission_classes = [permissions.AllowAny]
    queryset           = EthiopianFood.objects.filter(is_active=True)
    lookup_field       = "slug"


# ── Meal Logging & Feed ───────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def log_meal(request):
    """
    POST /api/v1/foods/log/
    Accepts food_ids + servings → scoring engine → saves MealLog
    """
    serializer = MealLogCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    food_items_data = data["foods"]
    food_ids        = [item["food_id"] for item in food_items_data]
    db_foods        = {
        str(f.id): f
        for f in EthiopianFood.objects.filter(id__in=food_ids, is_active=True)
    }

    if not db_foods:
        return Response({"error": "No valid foods found."}, status=400)

    food_items = []
    for item in food_items_data:
        food_id  = str(item["food_id"])
        db_food  = db_foods.get(food_id)
        if not db_food:
            continue
        food_items.append(FoodItem(
            slug               = db_food.slug,
            fiber_g            = db_food.fiber_g,
            protein_g          = db_food.protein_g,
            iron_mg            = db_food.iron_mg,
            fermentation_score = db_food.fermentation_score,
            inflammatory_index = db_food.inflammatory_index,
            prebiotic_score    = db_food.prebiotic_score,
            glycemic_index     = db_food.glycemic_index,
            servings           = float(item.get("servings", 1.0)),
        ))

    profile = getattr(request.user, "profile", None)
    context = UserContext(
        is_pregnant    = getattr(profile, "is_pregnant",         False),
        has_diabetes   = getattr(profile, "has_diabetes",        False),
        has_anemia     = getattr(profile, "has_anemia",          False),
        is_fasting     = getattr(profile, "is_fasting_season",   False),
        age            = getattr(profile, "age",                  None),
        primary_goal   = getattr(profile, "primary_goal",   "general"),
    )

    result = compute_gut_score(food_items, context)

    meal_log = MealLog.objects.create(
        user               = request.user,
        date               = data["date"],
        meal_type          = data["meal_type"],
        notes              = data.get("notes", ""),
        gut_score          = result.gut_score,
        fiber_g_total      = result.fiber_g,
        protein_g_total    = result.protein_g,
        iron_mg_total      = result.iron_mg,
        fermentation_total = result.fermentation_total,
        inflammatory_net   = result.inflammatory_net,
    )

    for item in food_items_data:
        food_id = str(item["food_id"])
        db_food = db_foods.get(food_id)
        if db_food:
            MealLogFood.objects.create(
                meal_log = meal_log,
                food     = db_food,
                servings = float(item.get("servings", 1.0)),
            )

    _update_daily_nutrition(request.user, data["date"], result)

    return Response({
        "meal_log_id":    str(meal_log.id),
        "gut_score":      result.gut_score,
        "label":          result.label,
        "color":          result.color,
        "fiber_g":        result.fiber_g,
        "protein_g":      result.protein_g,
        "iron_mg":        result.iron_mg,
        "fermentation_total": result.fermentation_total,
        "inflammatory_net":   result.inflammatory_net,
        "sub_scores": {
            "fiber":        result.fiber_sub,
            "fermentation": result.fermentation_sub,
            "inflammation": result.inflammation_sub,
            "protein":      result.protein_sub,
        },
        "alerts":              result.alerts,
        "kuriftu_tip":         result.kuriftu_tip,
        "top_foods":           result.top_foods,
        "weakest_dimension":   result.weakest_dimension,
    }, status=201)


class MealLogListView(generics.ListAPIView):
    """GET /api/v1/foods/logs/?date=2026-06-06"""
    serializer_class   = MealLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class   = None

    def get_queryset(self):
        qs = MealLog.objects.filter(user=self.request.user)
        date_param = self.request.query_params.get("date")
        if date_param:
            qs = qs.filter(date=date_param)
        return qs


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def dashboard_feed(request):
    """
    GET /api/v1/foods/feed/
    Serves the dashboard meal feed timeline. Maps to your log network parameters.
    """
    logs = MealLog.objects.filter(user=request.user).order_by("-date", "-created_at")[:15]
    serializer = MealLogSerializer(logs, many=True)
    return Response(serializer.data)


# ── Daily / Weekly Nutrition ──────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def daily_nutrition(request):
    """GET /api/v1/foods/daily/?date=2026-06-06"""
    target_date = request.query_params.get("date", str(date.today()))
    try:
        record = DailyNutrition.objects.get(user=request.user, date=target_date)
        return Response(DailyNutritionSerializer(record).data)
    except DailyNutrition.DoesNotExist:
        return Response({"gut_score": 0, "message": "No meals logged yet today."})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def weekly_nutrition(request):
    """GET /api/v1/foods/weekly/"""
    today          = date.today()
    seven_days_ago = today - timedelta(days=6)
    records        = DailyNutrition.objects.filter(
        user     = request.user,
        date__gte = seven_days_ago,
        date__lte = today,
    ).order_by("date")

    return Response({
        "week_data":     DailyNutritionSerializer(records, many=True).data,
        "avg_gut_score": _average([r.gut_score for r in records]),
        "avg_fiber_g":   _average([r.fiber_g   for r in records]),
        "best_day": (
            max(
                records,
                key=lambda r: r.gut_score,
            ).date.strftime("%A")
            if records else None
        ),
    })


# ── Internal helpers ──────────────────────────────────────────────────────────

def _update_daily_nutrition(user, log_date, score_result):
    """Upsert the DailyNutrition aggregate for a given day safely."""
    record, _ = DailyNutrition.objects.get_or_create(
        user    = user,
        date    = log_date,
        defaults = {"gut_score": 0, "meal_count": 0, "fiber_g": 0, "protein_g": 0, "iron_mg": 0, "fermentation_total": 0, "inflammatory_net": 0},
    )

    all_today = MealLog.objects.filter(user=user, date=log_date)
    if all_today.exists():
        count = all_today.count()
        record.gut_score = int(sum(m.gut_score for m in all_today) / count)
        
        # Recalculate pure totals dynamically from logged historical rows instead of adding raw increments
        record.fiber_g            = sum(m.fiber_g_total for m in all_today)
        record.protein_g          = sum(m.protein_g_total for m in all_today)
        record.iron_mg            = sum(m.iron_mg_total for m in all_today)
        record.fermentation_total = sum(m.fermentation_total for m in all_today)
        record.inflammatory_net   = sum(m.inflammatory_net for m in all_today)
        record.meal_count         = count
    
    record.kuriftu_tip = score_result.kuriftu_tip
    record.save()

    profile = getattr(user, "profile", None)
    if profile:
        profile.current_gut_score = record.gut_score
        profile.save(update_fields=["current_gut_score"])


def _average(values: list) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0