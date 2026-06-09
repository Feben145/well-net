"""
wellness/views.py
━━━━━━━━━━━━━━━━━
AI recommendations, nutrition guide, weekly meal planner.

ALL food data is sourced from the EPHI 2025 PDF import via:
  wellness.food_source  →  foods.models.EthiopianFood

No seed files, no hardcoded food lists.
"""
from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from foods.serializers import FoodSerializer
from .food_source import (
    get_foods,
    get_recommendation_pool,
    build_weekly_plan,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _profile_context(user) -> dict:
    """Extract health context from the user's profile."""
    profile = getattr(user, "profile", None)
    return {
        "is_pregnant":   getattr(profile, "is_pregnant",       False),
        "has_diabetes":  getattr(profile, "has_diabetes",       False),
        "has_anemia":    getattr(profile, "has_anemia",         False),
        "is_fasting":    getattr(profile, "is_fasting_season",  False),
        "goal":          getattr(profile, "primary_goal",  "general"),
        "age":           getattr(profile, "age",                 None),
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI Recommendations
# GET /api/v1/wellness/recommendations/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_ai_recommendations(request):
    """
    Return a ranked list of recommended foods personalised for the
    user's health profile.

    Source: EPHI 2025 database (parse_ephi_pdf).
    Display names include Amharic in brackets: "Misir Wot  [ምሥር ወጥ]"
    """
    ctx   = _profile_context(request.user)
    foods = get_recommendation_pool(
        is_pregnant  = ctx["is_pregnant"],
        has_diabetes = ctx["has_diabetes"],
        is_fasting   = ctx["is_fasting"],
        has_anemia   = ctx["has_anemia"],
        goal         = ctx["goal"],
    )

    # Build response items (top 10)
    items = []
    for food in foods[:10]:
        items.append({
            "id":           food.id,
            "slug":         food.slug,
            # display_name: "Injera teff  [እንጀራ]" — Amharic in brackets
            "display_name": food.get_display_name(),
            "name_en":      food.name_en,
            "name_am":      food.name_am,
            "category":     food.category,
            "calories_kcal": food.calories_kcal,
            "fiber_g":      food.fiber_g,
            "protein_g":    food.protein_g,
            "iron_mg":      food.iron_mg,
            "fermentation_score": food.fermentation_score,
            "glycemic_index":     food.glycemic_index,
            "inflammatory_index": food.inflammatory_index,
            "fasting_safe":       food.fasting_safe,
            "pregnancy_safe":     food.pregnancy_safe,
            "diabetes_friendly":  food.diabetes_friendly,
            "reason": _recommendation_reason(food, ctx),
        })

    return Response({
        "goal":            ctx["goal"],
        "filters_applied": {
            "pregnancy_safe":  ctx["is_pregnant"],
            "diabetes_filter": ctx["has_diabetes"],
            "fasting_filter":  ctx["is_fasting"],
            "anemia_filter":   ctx["has_anemia"],
        },
        "recommendations": items,
        "source":          "EPHI Food Composition Table 2025",
    })


def _recommendation_reason(food, ctx: dict) -> str:
    """Short human-readable reason why this food was recommended."""
    reasons = []
    if food.fermentation_score >= 2:
        reasons.append("high probiotic value")
    if food.prebiotic_score >= 2:
        reasons.append("rich in prebiotic fibre")
    if food.inflammatory_index <= -1:
        reasons.append("anti-inflammatory")
    if ctx["has_anemia"] and food.iron_mg >= 3:
        reasons.append(f"good iron source ({food.iron_mg:.1f} mg)")
    if ctx["has_diabetes"] and food.glycemic_index and food.glycemic_index <= 40:
        reasons.append(f"low glycaemic index ({food.glycemic_index})")
    if ctx["is_pregnant"] and food.protein_g >= 5:
        reasons.append("supports pregnancy protein needs")
    if ctx["is_fasting"] and food.fasting_safe:
        reasons.append("fasting-compatible")
    if not reasons:
        reasons.append("balanced nutritional profile")
    return "; ".join(reasons).capitalize()


# ─────────────────────────────────────────────────────────────────────────────
# Nutrition Guide
# GET /api/v1/wellness/nutrition-guide/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def nutrition_guide(request):
    """
    Category-organised nutrition reference.
    Sourced entirely from the EPHI 2025 database.

    Amharic names are included in display_name: "Ayib  [አይብ]"
    """
    categories = [
        "grains", "legumes", "meat", "dairy",
        "vegetables", "drinks", "special",
    ]

    guide: dict[str, list[dict]] = {}
    for cat in categories:
        foods = get_foods(category=cat)
        guide[cat] = [
            {
                "slug":         f.slug,
                # "Teff injera  [ጤፍ እንጀራ]"
                "display_name": f.get_display_name(),
                "name_en":      f.name_en,
                "name_am":      f.name_am,
                "calories_kcal": f.calories_kcal,
                "fiber_g":      f.fiber_g,
                "protein_g":    f.protein_g,
                "iron_mg":      f.iron_mg,
                "glycemic_index":     f.glycemic_index,
                "fermentation_score": f.fermentation_score,
                "inflammatory_index": f.inflammatory_index,
                "fasting_safe":       f.fasting_safe,
                "pregnancy_safe":     f.pregnancy_safe,
                "diabetes_friendly":  f.diabetes_friendly,
                "notes":              f.notes,
            }
            for f in foods
        ]

    return Response({
        "guide":  guide,
        "source": "EPHI Food Composition Table 2025",
        "note":   (
            "All nutritional values are per 100 g edible portion. "
            "Amharic names shown in brackets [አማርኛ] for Ethiopian foods."
        ),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Weekly Meal Planner
# GET /api/v1/wellness/meal-plan/
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def weekly_meal_plan(request):
    """
    Generate a 7-day meal plan personalised to the user's health profile.

    Safety guarantees (all enforced in food_source.build_weekly_plan):
    • Each food appears at most once per day.
    • Planner-limited foods (tej, raw meat, etc.) appear ≤ 1 × per week.
    • Category daily limits respected (e.g. max 2 grain slots/day).
    • No two consecutive days with the same food.
    • All health filters applied (pregnancy, diabetes, fasting, anemia).

    Food names include Amharic in brackets: "Shiro Wot  [ሽሮ ወጥ]"
    Source: EPHI 2025 database.
    """
    ctx = _profile_context(request.user)

    plan = build_weekly_plan(
        is_pregnant  = ctx["is_pregnant"],
        has_diabetes = ctx["has_diabetes"],
        is_fasting   = ctx["is_fasting"],
        has_anemia   = ctx["has_anemia"],
        goal         = ctx["goal"],
    )

    return Response({
        "plan":   plan,
        "goal":   ctx["goal"],
        "filters": {
            "pregnancy":  ctx["is_pregnant"],
            "diabetes":   ctx["has_diabetes"],
            "fasting":    ctx["is_fasting"],
            "anemia":     ctx["has_anemia"],
        },
        "source": "EPHI Food Composition Table 2025",
        "note": (
            "Each day shows breakfast / lunch / dinner / snack. "
            "Food names include Amharic in brackets [አማርኛ]. "
            "Nutritional values per 100 g edible portion."
        ),
    })
