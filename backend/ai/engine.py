"""
ai/engine.py — Well-Net AI Wellness Engine (Groq API)

Design rules:
1. EVERY food referenced anywhere (tips, meal plan, feed) comes from
   foods.models.EthiopianFood — your EPHI-parsed database. There is
   NO hardcoded food fallback list anymore. If the DB has no foods,
   we say so honestly instead of inventing data.
2. Tips are structured as actionable items with an `action` field
   so the frontend can render real buttons (Log this food / View
   recipe / Book Kuriftu) instead of static paragraphs.
3. Every public function NEVER raises — it always returns a dict/list
   the view can serialize, even on total failure, so this file can
   never be the cause of a 500.
4. Meal plans maximize variety: foods are drawn across categories
   (grains, legumes, meat, dairy_poultry, vegetables, drinks, special)
   and the planner avoids repeating the same food — and avoids
   over-using the same category — across a single day and across
   the week wherever the food pool allows it.
"""
from __future__ import annotations
import json
import logging
import random
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    _client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
except Exception as e:
    logger.warning(f"Well-Net AI: groq client unavailable — {e}")
    _client = None

# Model used for all Groq chat completions in this file.
# Swap this if your Groq account uses a different hosted model.
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are Hana, Well-Net's AI wellness coach.
Well-Net is an Ethiopian wellness lifestyle ecosystem — not a medical app.

Your role:
- Provide warm, encouraging, practical wellness guidance
- ONLY recommend foods from the approved Ethiopian food list given to you in each prompt
- Never invent or suggest foods not on the approved list
- Reference Kuriftu Resort wellness experiences when relevant
- Never diagnose. Always suggest consulting a professional for medical issues.

Tone: warm, motivating, culturally proud. Like a knowledgeable Ethiopian friend."""


# ── Category model ──────────────────────────────────────────────────────────
# Matches the frontend CATEGORIES list (id values) so meal-plan variety logic
# lines up with how foods are actually categorized in the DB.
CATEGORY_IDS = [
    "grains",
    "legumes",
    "meat",
    "dairy_poultry",
    "vegetables",
    "drinks",
    "special",
]
CATEGORY_LABELS = {
    "grains":        "Grains & Teff",
    "legumes":       "Legumes / Wot",
    "meat":          "Meat & Fish",
    "dairy_poultry": "Dairy & Poultry",
    "vegetables":    "Vegetables",
    "drinks":        "Beverages",
    "special":       "Special/Fats",
}

# MAIN categories occupy actual meal slots (breakfast/lunch/dinner "foods").
# EXTRA categories (drinks, special/fats) are sides or accompaniments — they
# should never be the only thing standing in for a meal, and never count
# toward "main dish" variety the way grains/legumes/meat/veg/dairy do.
MAIN_CATEGORY_IDS  = ["grains", "legumes", "meat", "dairy_poultry", "vegetables"]
EXTRA_CATEGORY_IDS = ["drinks", "special"]

# Categories that are inherently animal products. On fasting days (Wed/Fri in
# the Ethiopian Orthodox tradition this app follows) these are excluded by
# CATEGORY regardless of what an individual food's `fasting_safe` flag says
# in the database — this is a hard rule, not just a data-trust assumption,
# since a bad EPHI import could otherwise mark a meat/dairy item as
# fasting-safe by mistake and nothing else in the code would catch it.
ANIMAL_PRODUCT_CATEGORIES = {"meat", "dairy_poultry"}


def _is_fasting_compliant(food: dict, is_fasting: bool) -> bool:
    """Single source of truth for 'can this food appear on a fasting day'.
    Combines the DB's fasting_safe flag with a hard category-level block on
    animal products, so fasting days can never include meat/dairy/poultry
    even if a food's fasting_safe flag is wrong."""
    if not is_fasting:
        return True
    if food.get("category") in ANIMAL_PRODUCT_CATEGORIES:
        return False
    return bool(food.get("fasting_safe"))



# ── DB access — single source of truth ─────────────────────────────────────────

def _get_db_foods() -> list[dict]:
    """
    Pull every active food straight from the EPHI-parsed database.
    Returns [] (not an exception) if the table is empty or the query fails,
    so callers can decide how to degrade gracefully.
    """
    try:
        from foods.models import EthiopianFood
        qs = EthiopianFood.objects.filter(is_active=True).values(
            "slug", "name_en", "name_am", "category",
            "fasting_safe", "pregnancy_safe", "diabetes_friendly",
            "fermentation_score", "fiber_g", "protein_g", "iron_mg",
            "glycemic_index",
        )
        out = []
        for f in qs:
            out.append({
                "slug":              f["slug"],
                "name":              _short_name(f["name_en"]),
                "amharic":           f["name_am"] or "",
                "category":          f["category"] or "special",
                "fasting_safe":      bool(f["fasting_safe"]),
                "pregnancy_safe":    bool(f["pregnancy_safe"]),
                "diabetes_friendly": bool(f["diabetes_friendly"]),
                "fermentation_score": f["fermentation_score"] or 0,
                "fiber_g":           f["fiber_g"] or 0,
                "protein_g":         f["protein_g"] or 0,
                "iron_mg":           f["iron_mg"] or 0,
                "glycemic_index":    f["glycemic_index"] or 0,
            })
        return out
    except Exception as e:
        logger.error(f"Well-Net AI: could not load foods from DB — {e}")
        return []


def _short_name(name_en: str) -> str:
    return (name_en or "").split(" — ")[0].split(" (")[0].strip()


# ── Public: wellness tips (button-ready) ───────────────────────────────────────

def get_wellness_tips(
    gut_score: int,
    weakest_dimension: str,
    top_foods: list[str],
    profile_context: dict,
    language: str = "en",
) -> dict:
    """
    Returns:
    {
      "wellness_message": str,
      "tips": [
        {
          "title": str, "body": str, "icon": str, "color": str,
          "action": {
            "type": "log_food" | "view_recipe" | "book_kuriftu" | "none",
            "label": str,            # button text
            "food_slug": str | None  # if type == log_food / view_recipe
          }
        }, ...
      ],
      "kuriftu_tip": str
    }
    """
    db_foods = _get_db_foods()

    if not db_foods:
        return _empty_db_tips(gut_score)

    if not _client:
        return _rule_based_tips(gut_score, weakest_dimension, db_foods, profile_context)

    prompt = _build_tip_prompt(gut_score, weakest_dimension, top_foods, db_foods, profile_context, language)
    try:
        response = _client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=700,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw_text = response.choices[0].message.content
        result = _parse_json_response(raw_text)
        if result and "tips" in result:
            return _attach_actions(result, db_foods)
        return _rule_based_tips(gut_score, weakest_dimension, db_foods, profile_context)
    except Exception as e:
        logger.warning(f"Well-Net AI: tips generation failed — {e}")
        return _rule_based_tips(gut_score, weakest_dimension, db_foods, profile_context)


def _attach_actions(result: dict, db_foods: list[dict]) -> dict:
    """Post-process the model's tips to attach a button action, matching mentioned foods to real slugs."""
    by_name = {f["name"].lower(): f for f in db_foods}
    tips = result.get("tips", [])
    for tip in tips:
        if "action" in tip:
            continue
        body_lower = (tip.get("body", "") + " " + tip.get("title", "")).lower()
        matched = next((f for n, f in by_name.items() if n in body_lower), None)
        if matched:
            tip["action"] = {
                "type": "log_food",
                "label": f"Log {matched['name']}",
                "food_slug": matched["slug"],
            }
        else:
            tip["action"] = {"type": "none", "label": "", "food_slug": None}
    result["tips"] = tips
    return result


# ── Public: meal plan ──────────────────────────────────────────────────────────

def get_meal_plan(
    family_members: list[dict],
    days: int = 7,
    language: str = "en",
) -> dict:
    """
    Build a {days}-day Ethiopian meal plan using ONLY foods present in the
    EPHI-parsed database right now. If the DB is empty, returns a clear
    error dict instead of inventing food data.

    Variety rule: across each day (and where the food pool allows it,
    across the week) meals should draw from different categories —
    grains, legumes, meat, dairy_poultry, vegetables, drinks, special —
    rather than repeating the same food or leaning on a single category.
    """
    db_foods = _get_db_foods()

    if not db_foods:
        return {
            "error": "No foods found in the database yet. Run the EPHI parser first (python manage.py parse_ephi_pdf) before generating a meal plan.",
            "days": [],
            "shopping_list": [],
        }

    all_names      = [f["name"] for f in db_foods]
    food_by_name   = {f["name"]: f for f in db_foods}
    # Hard rule for what's shown to the model as "fasting-safe": animal
    # products are excluded by category regardless of the DB's fasting_safe
    # flag, so the model is never shown a mislabeled meat/dairy item as an
    # option for Wednesday/Friday.
    fasting_names  = [f["name"] for f in db_foods if _is_fasting_compliant(f, True)]
    pregnancy_safe = [f["name"] for f in db_foods if f["pregnancy_safe"]]
    diabetes_safe  = [f["name"] for f in db_foods if f["diabetes_friendly"]]

    if not fasting_names:
        # Guarantee fasting days are always satisfiable, but still respect
        # the hard animal-product rule even in this fallback.
        non_animal = [n for n in all_names if food_by_name[n]["category"] not in ANIMAL_PRODUCT_CATEGORIES]
        fasting_names = non_animal[:5] or all_names[:5]

    has_pregnant = any("pregnant" in m.get("conditions", []) for m in family_members)
    has_diabetic = any("diabetes" in m.get("conditions", []) for m in family_members)

    if not _client:
        return _rule_based_meal_plan(db_foods, days, has_pregnant, has_diabetic)

    members_str = json.dumps(family_members, indent=2)

    # Build a category breakdown the model can use to actively balance the plan.
    by_category = {cat: [f["name"] for f in db_foods if f["category"] == cat] for cat in CATEGORY_IDS}
    category_block = "\n".join(
        f"{CATEGORY_LABELS[cat]} ({cat}):\n" + "\n".join("  • " + n for n in names)
        for cat, names in by_category.items() if names
    )

    prompt = f"""Create a {days}-day Ethiopian family meal plan.

FAMILY MEMBERS:
{members_str}

═══════════════════════════════════════════════════════════════════
CRITICAL RULES — FOLLOW EXACTLY:
1. You may ONLY use food names from the APPROVED LIST below — nothing else.
2. No oils, mayonnaise, processed foods, or anything off-list.
3. Each meal's "foods" array = separate individual items, not one combined dish name.
4. Each meal needs a one-sentence "note" describing how they're eaten together.
5. Wednesday and Friday MUST be fasting days. On these days, NEVER include
   ANY food from the Meat & Fish or Dairy & Poultry categories — no
   exceptions, regardless of any other consideration. Only grains, legumes,
   vegetables, drinks, and special/fats are allowed on fasting days.
6. CATEGORY ROLES — Beverages (drinks) and Special/Fats (special) are
   ACCOMPANIMENTS, not main dishes:
   - Every meal's "foods" array must include at least one item from a MAIN
     category (Grains, Legumes, Meat & Fish, Dairy & Poultry, or Vegetables).
   - Drinks and Special/Fats items may be ADDED alongside main foods (e.g.
     Buna with breakfast, Berbere seasoning a dish) but must never be the
     only item in a meal, and must never fill a meal slot in place of an
     actual dish.
7. VARIETY IS REQUIRED:
   - Do not repeat the exact same food within the same day.
   - Avoid repeating the same food on consecutive days.
   - Each meal should draw from MULTIPLE main categories (e.g. a grain +
     a legume or vegetable + where appropriate a protein/dairy source),
     not just one category repeated.
   - Across the week, rotate through ALL available main categories rather
     than leaning on one or two. If a category has multiple options, use
     different ones across the week instead of repeating the same item.
8. Make it feel like a real week: balance fiber, protein, fermented foods, and iron
   across the week rather than cramming everything into one day.
9. Food names MUST be copied EXACTLY, character-for-character, from the
   APPROVED FOODS list below. Do not abbreviate, translate, transliterate,
   invent, or output numbers/placeholders as food names. If you are unsure
   which approved food to use, pick any food from the APPROVED FOODS list —
   never output a name that is not in that list verbatim.
═══════════════════════════════════════════════════════════════════

APPROVED FOODS BY CATEGORY:
{category_block}

FASTING-SAFE FOODS (Wednesday + Friday only):
{chr(10).join("• " + n for n in fasting_names)}

{"PREGNANCY-SAFE ONLY for pregnant members:" + chr(10) + chr(10).join("• " + n for n in pregnancy_safe) if has_pregnant else ""}
{"DIABETES-FRIENDLY ONLY for diabetic members:" + chr(10) + chr(10).join("• " + n for n in diabetes_safe) if has_diabetic else ""}

Return ONLY this JSON shape, no markdown fences, no extra text:
{{
  "days": [
    {{
      "day": 1,
      "day_name": "Monday",
      "is_fasting_day": false,
      "meals": {{
        "breakfast": {{"foods": ["Injera", "Buna"], "note": "..."}},
        "lunch":     {{"foods": ["Injera", "Misir wot", "Gomen"], "note": "..."}},
        "dinner":    {{"foods": ["Injera", "Shiro wot"], "note": "..."}}
      }}
    }}
  ],
  "shopping_list": ["Injera", "Misir wot", "Shiro", "Gomen"]
}}"""

    try:
        response = _client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=3000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw_text = response.choices[0].message.content
        result = _parse_json_response(raw_text)
        if not result or "days" not in result:
            return _rule_based_meal_plan(db_foods, days, has_pregnant, has_diabetic)
        return _validate_and_clean_plan(result, db_foods, fasting_names)
    except Exception as e:
        logger.warning(f"Well-Net AI: meal plan generation failed — {e}")
        return _rule_based_meal_plan(db_foods, days, has_pregnant, has_diabetic)


# ── Public: wellness journey feed ──────────────────────────────────────────────

def get_wellness_journey_feed(
    gut_score: int,
    weekly_avg: float,
    streak_days: int,
    profile: dict,
) -> list[dict]:
    db_foods = _get_db_foods()
    food_names = [f["name"] for f in db_foods] or ["your logged foods"]

    if not _client:
        return _rule_based_feed(gut_score, weekly_avg, streak_days, food_names)

    prompt = f"""Generate a wellness journey feed for this user:
- Today's gut score: {gut_score}/100
- Weekly average: {weekly_avg}/100
- Wellness streak: {streak_days} days
- Primary goal: {profile.get("primary_goal", "general wellness")}
- Is fasting: {profile.get("is_fasting_season", False)}
- Kuriftu guest: {profile.get("kuriftu_guest", False)}

Create 4 feed cards as a JSON array. When mentioning food, ONLY use names from this list:
{", ".join(food_names)}

[
  {{"type": "insight", "title": "", "body": "", "cta_label": null, "cta_action": null, "color": "teal"}}
]

Types: insight | tip | retreat | challenge | milestone
Colors: teal | amber | purple | green
The retreat card must reference a real Kuriftu experience (yoga with Weini, Mystic Nights sound healing, Boston Day Spa, gut reset retreat)."""

    try:
        response = _client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=800,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw_text = response.choices[0].message.content
        result = _parse_json_response(raw_text, expect_list=True)
        return result if isinstance(result, list) else _rule_based_feed(gut_score, weekly_avg, streak_days, food_names)
    except Exception as e:
        logger.warning(f"Well-Net AI: feed generation failed — {e}")
        return _rule_based_feed(gut_score, weekly_avg, streak_days, food_names)


# ── JSON parsing helper ────────────────────────────────────────────────────────

def _parse_json_response(raw: str, expect_list: bool = False):
    try:
        clean = (raw or "").replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception as e:
        logger.warning(f"Well-Net AI: could not parse model JSON — {e}")
        return [] if expect_list else None


# ── Validation for meal plans ──────────────────────────────────────────────────

def _validate_and_clean_plan(plan: dict, db_foods: list[dict], fasting_names: list[str]) -> dict:
    """
    Cleans the model's output AND enforces variety as a safety net:
    - drops/replaces foods not in the approved DB list
    - if the model repeated a food within the same day, swaps the repeat
      for an unused food from an under-represented category where possible
    """
    all_names_lower     = {f["name"].lower(): f["name"] for f in db_foods}
    fasting_names_lower = {n.lower() for n in fasting_names}
    food_by_name         = {f["name"]: f for f in db_foods}

    def _looks_like_real_food_string(s: str) -> bool:
        """
        Reject garbage before we even try to match it: pure numbers, empty
        strings, or single-character noise. This stops things like a stray
        '2' or an unmatchable transliteration (e.g. 'kenewuhaw') from ever
        reaching the substring-matching fallback below, where they could
        accidentally match the wrong food.
        """
        s = (s or "").strip()
        if not s or len(s) < 3:
            return False
        if s.replace(".", "").replace(",", "").isdigit():
            return False
        return True

    def resolve(food_str: str, is_fasting: bool):
        if not _looks_like_real_food_string(food_str):
            return None
        key = str(food_str).lower().strip()
        if key in all_names_lower:
            name = all_names_lower[key]
            food = food_by_name.get(name)
            if food and _is_fasting_compliant(food, is_fasting):
                return name
            return None
        # Substring fallback only as a last resort, and only against names
        # that are a meaningfully close length match — prevents e.g. a short
        # garbled token from spuriously matching an unrelated long food name.
        candidates = [
            v for k, v in all_names_lower.items()
            if (key in k or k in v.lower()) and abs(len(key) - len(k)) <= 4
        ]
        for match in candidates:
            food = food_by_name.get(match)
            if food and _is_fasting_compliant(food, is_fasting):
                return match
        return None

    def category_counts(names: list[str]) -> dict:
        counts = {cat: 0 for cat in CATEGORY_IDS}
        for n in names:
            f = food_by_name.get(n)
            if f:
                counts[f["category"]] = counts.get(f["category"], 0) + 1
        return counts

    def pick_replacement(used_today: set, is_fasting: bool, day_counts: dict, week_food_counts: dict, week_cat_counts: dict, prefer_main: bool = True):
        """Prefer a food not yet used today, weighing both how often this food
        and how often its category have already been used THIS WEEK (not just
        today) — so a food/category that appeared Monday and Tuesday is less
        likely to be picked again Wednesday, spreading variety across the
        whole 7-day plan instead of only within a single day.
        Hard rule: on fasting days, animal-product categories are excluded
        regardless of the food's own fasting_safe flag.
        When prefer_main is True, foods from MAIN_CATEGORY_IDS are tried
        first — drinks/special are only used as a last resort, since they're
        accompaniments, not meal-filling dishes.
        Ties are broken randomly so refreshing produces real variation."""
        candidates = [
            f for f in db_foods
            if f["name"] not in used_today and _is_fasting_compliant(f, is_fasting)
        ]
        if not candidates:
            return None
        random.shuffle(candidates)
        if prefer_main:
            main_candidates = [f for f in candidates if f["category"] in MAIN_CATEGORY_IDS]
            if main_candidates:
                candidates = main_candidates
        candidates.sort(key=lambda f: (
            week_food_counts.get(f["name"], 0),       # least-used food this week first
            week_cat_counts.get(f["category"], 0),    # then least-used category this week
            day_counts.get(f["category"], 0),          # then least-used category today
        ))
        return candidates[0]["name"]

    # Week-level counters — persist ACROSS days so the planner spreads foods
    # and categories over the whole week instead of only avoiding same-day repeats.
    week_food_counts: dict[str, int] = {}
    week_cat_counts: dict[str, int] = {cat: 0 for cat in CATEGORY_IDS}

    for day in plan.get("days", []):
        is_fasting = bool(day.get("is_fasting_day")) or day.get("day_name") in ("Wednesday", "Friday")
        meals = day.get("meals", {})

        # Resolve all foods for the day first, then dedupe/balance across the whole day.
        used_today: set[str] = set()
        day_counts = {cat: 0 for cat in CATEGORY_IDS}

        for meal_key in ("breakfast", "lunch", "dinner"):
            meal = meals.get(meal_key)
            if not isinstance(meal, dict):
                continue

            resolved = []
            for raw_food in meal.get("foods") or []:
                name = resolve(raw_food, is_fasting)
                if not name:
                    # Don't just drop it — replace with a real food from an
                    # under-used category so the slot doesn't silently shrink
                    # and so we don't fall back to a fixed deterministic list.
                    logger.info(f"Well-Net AI: could not resolve food '{raw_food}' — substituting")
                    name = pick_replacement(used_today, is_fasting, day_counts, week_food_counts, week_cat_counts)
                    if not name:
                        continue
                if name in used_today:
                    # Repeat within the day — swap for variety where the pool allows it.
                    replacement = pick_replacement(used_today, is_fasting, day_counts, week_food_counts, week_cat_counts)
                    if replacement and replacement not in used_today:
                        name = replacement
                    # if no replacement is available, fall through and allow the repeat
                elif week_food_counts.get(name, 0) >= 2:
                    # This food has already been used 2+ times earlier in the
                    # week — try to swap it for something fresher, but only
                    # if a genuinely different option exists.
                    replacement = pick_replacement(used_today, is_fasting, day_counts, week_food_counts, week_cat_counts)
                    if replacement and replacement != name and week_food_counts.get(replacement, 0) < week_food_counts.get(name, 0):
                        name = replacement
                resolved.append(name)
                used_today.add(name)
                f = food_by_name.get(name)
                if f:
                    day_counts[f["category"]] = day_counts.get(f["category"], 0) + 1
                    week_food_counts[name] = week_food_counts.get(name, 0) + 1
                    week_cat_counts[f["category"]] = week_cat_counts.get(f["category"], 0) + 1

            if not resolved:
                # Randomized, category-aware fallback instead of a fixed
                # slice of db_foods (which previously always picked the
                # same first 1-2 items, e.g. always 'Barley'). Uses the hard
                # fasting rule (animal products excluded by category), not
                # just the DB's fasting_safe flag.
                fallback_source = [f for f in db_foods if _is_fasting_compliant(f, is_fasting)]
                fallback_source = [f for f in fallback_source if f["name"] not in used_today] or fallback_source
                # Prefer MAIN categories for the fallback so we don't end up
                # seeding a meal with only a drink or a seasoning.
                main_fallback = [f for f in fallback_source if f["category"] in MAIN_CATEGORY_IDS]
                if main_fallback:
                    fallback_source = main_fallback
                sample_size = min(2, len(fallback_source))
                resolved = [f["name"] for f in random.sample(fallback_source, sample_size)] if fallback_source else []
                used_today.update(resolved)
                for n in resolved:
                    f = food_by_name.get(n)
                    if f:
                        week_food_counts[n] = week_food_counts.get(n, 0) + 1
                        week_cat_counts[f["category"]] = week_cat_counts.get(f["category"], 0) + 1

            # Guarantee: every meal must include at least one MAIN-category
            # food. If the model's picks were entirely drinks/special (or the
            # meal ended up empty), drinks/special are accompaniments, not
            # substitutes for an actual dish — add a main food on top.
            has_main = any(
                food_by_name.get(n, {}).get("category") in MAIN_CATEGORY_IDS
                for n in resolved
            )
            if not has_main:
                main_addition = pick_replacement(
                    set(resolved), is_fasting, day_counts, week_food_counts, week_cat_counts, prefer_main=True
                )
                if main_addition:
                    resolved.append(main_addition)
                    used_today.add(main_addition)
                    f = food_by_name.get(main_addition)
                    if f:
                        day_counts[f["category"]] = day_counts.get(f["category"], 0) + 1
                        week_food_counts[main_addition] = week_food_counts.get(main_addition, 0) + 1
                        week_cat_counts[f["category"]] = week_cat_counts.get(f["category"], 0) + 1

            meal["foods"] = resolved
            meal["note"] = meal.get("note") or meal.get("notes") or ""

    # Shopping list MUST reflect what's actually scheduled in the plan — never
    # re-sample the food pool independently, or you can end up with items in
    # the shopping list that don't appear in any meal (and vice versa).
    used_in_plan: list[str] = []
    for day in plan.get("days", []):
        for meal_key in ("breakfast", "lunch", "dinner"):
            meal = day.get("meals", {}).get(meal_key)
            if isinstance(meal, dict):
                for n in meal.get("foods") or []:
                    if n not in used_in_plan:
                        used_in_plan.append(n)

    plan["shopping_list"] = used_in_plan or [f["name"] for f in db_foods[:6]]


    return plan


# ── Rule-based fallbacks — built entirely from db_foods, never hardcoded ───────

def _empty_db_tips(gut_score: int) -> dict:
    return {
        "wellness_message": "Your food database is empty — run the EPHI parser to unlock personalised tips.",
        "tips": [{
            "title": "Load your food database",
            "body": "Run `python manage.py parse_ephi_pdf` to import verified Ethiopian foods before AI tips can work.",
            "icon": "leaf", "color": "amber",
            "action": {"type": "none", "label": "", "food_slug": None},
        }],
        "kuriftu_tip": "",
    }


def _pick(db_foods: list[dict], predicate, fallback_idx: int = 0):
    matches = [f for f in db_foods if predicate(f)]
    return matches[0] if matches else (db_foods[fallback_idx] if db_foods else None)


def _rule_based_tips(score: int, weakness: str, db_foods: list[dict], profile: dict) -> dict:
    high_fiber  = _pick(db_foods, lambda f: f["fiber_g"] >= 5)
    fermented   = _pick(db_foods, lambda f: f["fermentation_score"] >= 2)
    high_protein = _pick(db_foods, lambda f: f["protein_g"] >= 8)

    dim_food = {"fiber": high_fiber, "fermentation": fermented, "protein": high_protein}
    primary = dim_food.get(weakness) or high_fiber or (db_foods[0] if db_foods else None)

    label = "Great" if score >= 80 else "Good" if score >= 65 else "Keep improving"

    tips = []
    if primary:
        tips.append({
            "title": f"Try {primary['name']}",
            "body": f"{primary['amharic'] + ' — ' if primary['amharic'] else ''}great source to improve your {weakness}.",
            "icon": "leaf", "color": "teal",
            "action": {"type": "log_food", "label": f"Log {primary['name']}", "food_slug": primary["slug"]},
        })
    if fermented and fermented != primary:
        tips.append({
            "title": f"Add {fermented['name']}",
            "body": "Fermented foods support your gut microbiome naturally.",
            "icon": "heart", "color": "purple",
            "action": {"type": "log_food", "label": f"Log {fermented['name']}", "food_slug": fermented["slug"]},
        })
    tips.append({
        "title": "Kuriftu wellness moment",
        "body": "Your score qualifies for a Kuriftu wellness experience matched to your gut health.",
        "icon": "star", "color": "amber",
        "action": {"type": "book_kuriftu", "label": "Explore Kuriftu", "food_slug": None},
    })

    return {
        "wellness_message": f"{label} work! Your score of {score} shows real progress.",
        "tips": tips,
        "kuriftu_tip": "",
    }


def _rule_based_meal_plan(db_foods: list[dict], days: int, has_pregnant: bool, has_diabetic: bool) -> dict:
    """
    Build a varied week by rotating through CATEGORIES (not just a flat food
    list), so each meal pulls from different food groups and the planner
    naturally avoids stacking three grains — or three of anything — in a row.

    Variety is enforced at TWO levels:
    - per-day: a meal won't repeat the same food twice (used_today)
    - per-week: foods/categories used heavily on earlier days are
      deprioritized on later days (week_food_counts / week_cat_counts),
      and the category scan order is reshuffled each day so the same
      1-2 categories don't dominate every single day.
    """
    pool = db_foods[:]
    if has_pregnant:
        pool = [f for f in pool if f["pregnancy_safe"]] or pool
    if has_diabetic:
        pool = [f for f in pool if f["diabetes_friendly"]] or pool

    if not pool:
        return {"error": "No suitable foods found in the database for this meal plan.", "days": [], "shopping_list": []}

    # Hard rule: fasting pool excludes animal-product categories regardless
    # of each food's own fasting_safe flag (see _is_fasting_compliant).
    fasting_pool = [f for f in pool if _is_fasting_compliant(f, True)] or pool

    # Group the pool by category so we can rotate across food groups.
    def by_category(source: list[dict]) -> dict[str, list[dict]]:
        grouped = {cat: [f for f in source if f["category"] == cat] for cat in CATEGORY_IDS}
        return {cat: foods for cat, foods in grouped.items() if foods}

    pool_by_cat = by_category(pool)
    fasting_by_cat = by_category(fasting_pool) or pool_by_cat

    if not pool_by_cat:
        # No category data at all — fall back to treating everything as one group.
        pool_by_cat = {"all": pool}
        fasting_by_cat = {"all": fasting_pool}

    # Per-category rotation cursors so repeated calls (and successive days)
    # advance through each category's options instead of always picking #1.
    # Starting offset is randomized per call so clicking "refresh" produces a
    # genuinely different plan instead of replaying the same DB order.
    cursors: dict[str, int] = {
        cat: random.randrange(len(foods)) if foods else 0
        for cat, foods in pool_by_cat.items()
    }

    def next_from_category(cat: str, grouped: dict[str, list[dict]]):
        foods = grouped.get(cat)
        if not foods:
            return None
        idx = cursors.get(cat, 0) % len(foods)
        cursors[cat] = cursors.get(cat, 0) + 1
        return foods[idx]

    # Week-level usage counters — persist across the whole loop, not reset
    # per day, so days later in the week actively avoid foods/categories
    # that already dominated earlier days.
    week_food_counts: dict[str, int] = {}
    week_cat_counts: dict[str, int] = {cat: 0 for cat in CATEGORY_IDS}

    def build_meal(grouped: dict[str, list[dict]], used_today: set, category_order: list[str], n: int) -> list[dict]:
        """Pull up to n foods, preferring categories not yet used today AND
        not yet over-used this week, cycling through category_order."""
        picks = []
        cats_cycle = [c for c in category_order if c in grouped]
        if not cats_cycle:
            return picks

        # Sort the day's category scan order by how little they've been used
        # this week so far — categories that dominated earlier days sink to
        # the back of the queue instead of being tried first every time.
        cats_cycle = sorted(cats_cycle, key=lambda c: week_cat_counts.get(c, 0))

        attempts = 0
        i = 0
        while len(picks) < n and attempts < n * len(cats_cycle) + 5:
            cat = cats_cycle[i % len(cats_cycle)]
            candidate = next_from_category(cat, grouped)
            attempts += 1
            i += 1
            if not candidate or candidate["name"] in used_today:
                continue
            # Skip foods already heavily used this week if a fresher
            # same-category alternative exists; otherwise allow it rather
            # than leaving the meal short.
            if week_food_counts.get(candidate["name"], 0) >= 2:
                alt = next((
                    f for f in grouped.get(cat, [])
                    if f["name"] not in used_today and week_food_counts.get(f["name"], 0) < week_food_counts.get(candidate["name"], 0)
                ), None)
                if alt:
                    candidate = alt
            picks.append(candidate)
            used_today.add(candidate["name"])
            week_food_counts[candidate["name"]] = week_food_counts.get(candidate["name"], 0) + 1
            week_cat_counts[candidate["category"]] = week_cat_counts.get(candidate["category"], 0) + 1
        return picks

    # A typical Ethiopian plate centers on grains, then rotates through
    # legumes/meat/dairy_poultry/vegetables for the rest. Drinks and
    # Special/Fats are deliberately excluded here — they're accompaniments
    # added on top of the meal afterward, never substitutes for a main dish.
    # This is the PREFERRED order when all else is equal — build_meal
    # re-sorts it daily by week-usage so it doesn't rigidly repeat the same
    # pattern every day.
    primary_order = [c for c in ["grains", "legumes", "vegetables", "meat", "dairy_poultry"] if c in MAIN_CATEGORY_IDS]

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    out_days = []

    for i in range(min(days, 7)):
        day_name = day_names[i]
        is_fasting = day_name in ("Wednesday", "Friday")
        grouped = fasting_by_cat if is_fasting else pool_by_cat

        used_today: set[str] = set()

        b = build_meal(grouped, used_today, primary_order, 2)
        l = build_meal(grouped, used_today, primary_order, 3)
        d = build_meal(grouped, used_today, primary_order, 2)

        # Safety net: if categories were too sparse to fill a meal, top up
        # from anywhere in the day's MAIN-category pool (still avoiding
        # same-day repeats where possible), preferring the least week-used
        # foods. Drinks/special are excluded here too — see add_extra below.
        main_grouped = {cat: foods for cat, foods in grouped.items() if cat in MAIN_CATEGORY_IDS}

        def top_up(items: list[dict], n: int):
            if len(items) >= n:
                return items
            remaining = [f for foods in main_grouped.values() for f in foods if f["name"] not in used_today]
            random.shuffle(remaining)
            remaining.sort(key=lambda f: week_food_counts.get(f["name"], 0))
            for f in remaining:
                if len(items) >= n:
                    break
                items.append(f)
                used_today.add(f["name"])
                week_food_counts[f["name"]] = week_food_counts.get(f["name"], 0) + 1
                week_cat_counts[f["category"]] = week_cat_counts.get(f["category"], 0) + 1
            return items

        b = top_up(b, 2)
        l = top_up(l, 3)
        d = top_up(d, 2)

        # Last-resort safety net: an empty meal is worse than a same-day
        # repeat. If the main-category pool was too sparse to fill a meal
        # even after top_up (e.g. a tiny DB), allow repeating an
        # already-used main food rather than shipping a blank meal.
        def ensure_not_empty(items: list[dict]):
            if items:
                return items
            main_pool = [f for foods in main_grouped.values() for f in foods]
            if not main_pool:
                return items
            random.shuffle(main_pool)
            main_pool.sort(key=lambda f: week_food_counts.get(f["name"], 0))
            return [main_pool[0]]

        b = ensure_not_empty(b)
        l = ensure_not_empty(l)
        d = ensure_not_empty(d)

        # Optionally add ONE accompaniment (drink or special/fats) per meal —
        # never replacing a main dish, just riding alongside it, and only
        # ever a food that's allowed on this day (fasting-compliant if needed).
        extra_grouped = {cat: foods for cat, foods in grouped.items() if cat in EXTRA_CATEGORY_IDS}

        def add_extra(items: list[dict]):
            candidates = [
                f for foods in extra_grouped.values() for f in foods
                if f["name"] not in used_today and _is_fasting_compliant(f, is_fasting)
            ]
            if not candidates:
                return items
            random.shuffle(candidates)
            candidates.sort(key=lambda f: week_food_counts.get(f["name"], 0))
            pick = candidates[0]
            items.append(pick)
            used_today.add(pick["name"])
            week_food_counts[pick["name"]] = week_food_counts.get(pick["name"], 0) + 1
            week_cat_counts[pick["category"]] = week_cat_counts.get(pick["category"], 0) + 1
            return items

        b = add_extra(b)
        l = add_extra(l)
        d = add_extra(d)

        out_days.append({
            "day": i + 1,
            "day_name": day_name,
            "is_fasting_day": is_fasting,
            "meals": {
                "breakfast": {"foods": [f["name"] for f in b], "note": "Start the day light and energised."},
                "lunch":     {"foods": [f["name"] for f in l], "note": "Main meal of the day — balanced and filling."},
                "dinner":    {"foods": [f["name"] for f in d], "note": "Lighter evening meal, easy to digest."},
            },
        })

    # Shopping list MUST reflect what's actually scheduled across the week —
    # never independently re-sample the category pool, or items can show up
    # in the shopping list that no meal actually uses (and vice versa).
    shopping: list[str] = []
    for day in out_days:
        for meal_key in ("breakfast", "lunch", "dinner"):
            for name in day["meals"][meal_key]["foods"]:
                if name not in shopping:
                    shopping.append(name)
    if not shopping:
        shopping = list({f["name"] for f in pool[:10]})

    return {"days": out_days, "shopping_list": shopping}


def _rule_based_feed(score: int, weekly_avg: float, streak: int, food_names: list[str]) -> list[dict]:
    sample = food_names[0] if food_names else "your favourite Ethiopian food"
    return [
        {"type": "insight", "title": f"Your score: {score}/100", "body": f"Weekly average: {weekly_avg}. {'Trending up!' if score > weekly_avg else 'Keep going — consistency is everything.'}", "cta_label": None, "cta_action": None, "color": "teal"},
        {"type": "tip", "title": "Today's wellness tip", "body": f"Try {sample} today — small consistent choices add up.", "cta_label": "Log a meal", "cta_action": "log_meal", "color": "amber"},
        {"type": "retreat", "title": "Kuriftu Wellness Experience", "body": "Kuriftu's Mystic Nights sound healing sessions are open this weekend.", "cta_label": "Learn more", "cta_action": "book_kuriftu", "color": "purple"},
        {"type": "challenge", "title": f"{streak}-day streak!", "body": "Keep your streak alive today.", "cta_label": "Log now", "cta_action": "log_meal", "color": "green"},
    ]


def _build_tip_prompt(score, weakness, top_foods, db_foods, profile, language) -> str:
    lang_note = "Respond in Amharic with English in brackets." if language == "am" else "Respond in English."
    food_names = [f["name"] for f in db_foods]
    return f"""User gut score: {score}/100
Weakest dimension: {weakness}
Top foods eaten today: {", ".join(top_foods) if top_foods else "none logged"}
Profile: {json.dumps(profile)}
{lang_note}

ONLY reference foods from this approved list (from our live database):
{", ".join(food_names)}

Give exactly 3 wellness tips as JSON:
{{
  "wellness_message": "One warm opening sentence acknowledging their score",
  "tips": [
    {{"title": "", "body": "", "icon": "leaf|heart|zap|star", "color": "teal|amber|purple"}},
    {{"title": "", "body": "", "icon": "...", "color": "..."}},
    {{"title": "", "body": "", "icon": "...", "color": "..."}}
  ]
}}"""