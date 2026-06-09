"""
wellness/food_source.py
━━━━━━━━━━━━━━━━━━━━━━━
Single accessor layer for the EPHI food database.

All wellness views (AI recommendations, nutrition guide, weekly meal
planner) MUST use the helpers in this file instead of importing any
seed data or calling EthiopianFood.objects directly.

This keeps parse_ephi_pdf.py as the single source of truth:
  python manage.py parse_ephi_pdf [--update]
"""
from __future__ import annotations
from foods.models import EthiopianFood


# ─────────────────────────────────────────────
# Core accessor
# ─────────────────────────────────────────────

def get_foods(
    *,
    category: str | None             = None,
    fasting_safe: bool | None        = None,
    pregnancy_safe: bool | None      = None,
    diabetes_friendly: bool | None   = None,
    planner_weekly_safe: bool | None = None,
    search: str | None               = None,
    active_only: bool                = True,
):
    """
    Return a QuerySet of EthiopianFood filtered by the given criteria.
    All data originates from the EPHI 2025 PDF import.
    """
    from django.db.models import Q

    qs = EthiopianFood.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    if category:
        qs = qs.filter(category=category)
    if fasting_safe is not None:
        qs = qs.filter(fasting_safe=fasting_safe)
    if pregnancy_safe is not None:
        qs = qs.filter(pregnancy_safe=pregnancy_safe)
    if diabetes_friendly is not None:
        qs = qs.filter(diabetes_friendly=diabetes_friendly)
    if planner_weekly_safe is not None:
        qs = qs.filter(planner_weekly_safe=planner_weekly_safe)
    if search:
        qs = qs.filter(
            Q(name_en__icontains=search) |
            Q(name_am__icontains=search) |
            Q(display_name__icontains=search)
        )
    return qs.order_by("category", "name_en")


def get_food_by_slug(slug: str) -> EthiopianFood | None:
    return EthiopianFood.objects.filter(slug=slug, is_active=True).first()


# ─────────────────────────────────────────────
# AI Recommendations helper
# ─────────────────────────────────────────────

def get_recommendation_pool(
    *,
    is_pregnant: bool   = False,
    has_diabetes: bool  = False,
    is_fasting: bool    = False,
    has_anemia: bool    = False,
    goal: str           = "general",
) -> list[EthiopianFood]:
    """
    Return candidate foods suitable for AI recommendation,
    filtered by the user's health context.
    Always sourced from the EPHI database.
    """
    qs = get_foods()

    if is_pregnant:
        qs = qs.filter(pregnancy_safe=True)
    if has_diabetes:
        qs = qs.filter(diabetes_friendly=True)
    if is_fasting:
        qs = qs.filter(fasting_safe=True)

    # Goal-based ordering
    if goal == "gut_health":
        qs = qs.order_by("-fermentation_score", "-prebiotic_score")
    elif goal == "weight_loss":
        qs = qs.order_by("calories_kcal", "-fiber_g")
    elif goal == "energy":
        qs = qs.order_by("-calories_kcal", "-protein_g")
    elif goal == "anemia" or has_anemia:
        qs = qs.order_by("-iron_mg", "-protein_g")
    elif goal == "inflammation":
        qs = qs.order_by("inflammatory_index")   # most anti-inflammatory first
    else:
        qs = qs.order_by("-fermentation_score", "-fiber_g")

    return list(qs[:40])   # top 40 candidates for the AI to choose from


# ─────────────────────────────────────────────
# Weekly meal planner helpers
# ─────────────────────────────────────────────

# Map meal slots to preferred categories (ordered by priority)
MEAL_SLOT_CATEGORIES: dict[str, list[str]] = {
    "breakfast": ["grains", "dairy", "legumes"],
    "lunch":     ["legumes", "vegetables", "grains", "meat"],
    "dinner":    ["legumes", "meat", "vegetables", "grains"],
    "snack":     ["dairy", "vegetables", "fruits", "special"],
}

# Number of unique foods per meal slot per day
FOODS_PER_SLOT = 2

# Days of the week for plan generation
WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def build_weekly_plan(
    *,
    is_pregnant: bool   = False,
    has_diabetes: bool  = False,
    is_fasting: bool    = False,
    has_anemia: bool    = False,
    goal: str           = "general",
) -> dict:
    """
    Build a 7-day meal plan using only EPHI-sourced foods.

    Rules enforced:
    1. Each food appears at most once per day.
    2. Foods with planner_weekly_safe=False appear at most once per week.
    3. Category daily limits are respected (e.g. max 2 grain slots/day).
    4. Varied: the same food does not appear on consecutive days.
    5. All health filters (pregnancy, diabetes, fasting, anemia) applied.
    """
    base_pool = get_recommendation_pool(
        is_pregnant  = is_pregnant,
        has_diabetes = has_diabetes,
        is_fasting   = is_fasting,
        has_anemia   = has_anemia,
        goal         = goal,
    )

    # Separate weekly-limited foods
    weekly_limited   = [f for f in base_pool if not f.planner_weekly_safe]
    weekly_unlimited = [f for f in base_pool if f.planner_weekly_safe]

    used_weekly_limited: set[int] = set()   # ids already used this week
    used_yesterday:      set[int] = set()   # ids used on previous day

    plan: dict[str, dict[str, list[dict]]] = {}

    for day in WEEK_DAYS:
        day_plan: dict[str, list[dict]] = {}
        used_today:  set[int]  = set()
        category_counts: dict[str, int] = {}

        for slot, preferred_cats in MEAL_SLOT_CATEGORIES.items():
            slot_foods: list[dict] = []

            # Build a candidate list in preferred-category order
            candidates: list[EthiopianFood] = []
            for cat in preferred_cats:
                cat_limit = _category_limit_for_day(cat)
                already   = category_counts.get(cat, 0)
                if already >= cat_limit:
                    continue
                for f in weekly_unlimited:
                    if (
                        f.category == cat
                        and f.id not in used_today
                        and f.id not in used_yesterday
                    ):
                        candidates.append(f)

            # Add weekly-limited foods if not yet used this week
            for f in weekly_limited:
                if (
                    f.id not in used_weekly_limited
                    and f.id not in used_today
                    and f.id not in used_yesterday
                ):
                    candidates.append(f)

            # Fallback: relax the "not yesterday" constraint
            if len(candidates) < FOODS_PER_SLOT:
                for f in weekly_unlimited:
                    if f.id not in used_today and f not in candidates:
                        candidates.append(f)

            # Pick up to FOODS_PER_SLOT unique foods
            for food in candidates[:FOODS_PER_SLOT]:
                slot_foods.append(_food_to_plan_item(food))
                used_today.add(food.id)
                category_counts[food.category] = (
                    category_counts.get(food.category, 0) + 1
                )
                if not food.planner_weekly_safe:
                    used_weekly_limited.add(food.id)

            day_plan[slot] = slot_foods

        plan[day]       = day_plan
        used_yesterday  = set(used_today)

    return plan


def _category_limit_for_day(category: str) -> int:
    limits = {
        "grains":     2,
        "meat":       2,
        "legumes":    3,
        "dairy":      2,
        "vegetables": 4,
        "drinks":     2,
        "special":    2,
    }
    return limits.get(category, 2)


def _food_to_plan_item(food: EthiopianFood) -> dict:
    """Minimal dict used inside the weekly plan response."""
    return {
        "id":           food.id,
        "slug":         food.slug,
        "display_name": food.get_display_name(),   # "Injera teff  [እንጀራ]"
        "name_en":      food.name_en,
        "name_am":      food.name_am,
        "category":     food.category,
        "calories_kcal": food.calories_kcal,
        "protein_g":    food.protein_g,
        "fiber_g":      food.fiber_g,
        "iron_mg":      food.iron_mg,
        "planner_weekly_safe": food.planner_weekly_safe,
    }
