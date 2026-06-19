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
    fasting_names  = [f["name"] for f in db_foods if f["fasting_safe"]]
    pregnancy_safe = [f["name"] for f in db_foods if f["pregnancy_safe"]]
    diabetes_safe  = [f["name"] for f in db_foods if f["diabetes_friendly"]]

    if not fasting_names:
        # Guarantee fasting days are always satisfiable
        fasting_names = all_names[:5]

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
5. Wednesday and Friday MUST be fasting days — only fasting-safe foods.
6. VARIETY IS REQUIRED:
   - Do not repeat the exact same food within the same day.
   - Avoid repeating the same food on consecutive days.
   - Each meal should draw from MULTIPLE categories below (e.g. a grain +
     a legume or vegetable + where appropriate a protein/dairy source),
     not just one category repeated.
   - Across the week, rotate through ALL available categories rather than
     leaning on one or two. If a category has multiple options, use
     different ones across the week instead of repeating the same item.
7. Make it feel like a real week: balance fiber, protein, fermented foods, and iron
   across the week rather than cramming everything into one day.
8. Food names MUST be copied EXACTLY, character-for-character, from the
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
            if not is_fasting or name.lower() in fasting_names_lower:
                return name
        # Substring fallback only as a last resort, and only against names
        # that are a meaningfully close length match — prevents e.g. a short
        # garbled token from spuriously matching an unrelated long food name.
        candidates = [
            v for k, v in all_names_lower.items()
            if (key in k or k in v.lower()) and abs(len(key) - len(k)) <= 4
        ]
        if candidates:
            match = candidates[0]
            if not is_fasting or match.lower() in fasting_names_lower:
                return match
        return None

    def category_counts(names: list[str]) -> dict:
        counts = {cat: 0 for cat in CATEGORY_IDS}
        for n in names:
            f = food_by_name.get(n)
            if f:
                counts[f["category"]] = counts.get(f["category"], 0) + 1
        return counts

    def pick_replacement(used_today: set, is_fasting: bool, counts: dict):
        """Prefer a food not yet used today, from the least-used category so far.
        Ties within the same category count are broken randomly so refreshing
        the plan produces real variation instead of always picking the same item."""
        candidates = [f for f in db_foods if f["name"] not in used_today]
        if is_fasting:
            candidates = [f for f in candidates if f["fasting_safe"]] or candidates
        if not candidates:
            return None
        random.shuffle(candidates)
        candidates.sort(key=lambda f: counts.get(f["category"], 0))
        return candidates[0]["name"]

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
                    name = pick_replacement(used_today, is_fasting, day_counts)
                    if not name:
                        continue
                if name in used_today:
                    # Repeat within the day — swap for variety where the pool allows it.
                    replacement = pick_replacement(used_today, is_fasting, day_counts)
                    if replacement and replacement not in used_today:
                        name = replacement
                    # if no replacement is available, fall through and allow the repeat
                resolved.append(name)
                used_today.add(name)
                f = food_by_name.get(name)
                if f:
                    day_counts[f["category"]] = day_counts.get(f["category"], 0) + 1

            if not resolved:
                # Randomized, category-aware fallback instead of a fixed
                # slice of db_foods (which previously always picked the
                # same first 1-2 items, e.g. always 'Barley').
                fallback_source = (
                    [f for f in db_foods if f["fasting_safe"]] if is_fasting
                    else db_foods
                )
                fallback_source = [f for f in fallback_source if f["name"] not in used_today] or fallback_source
                sample_size = min(2, len(fallback_source))
                resolved = [f["name"] for f in random.sample(fallback_source, sample_size)] if fallback_source else []
                used_today.update(resolved)

            meal["foods"] = resolved
            meal["note"] = meal.get("note") or meal.get("notes") or ""

    raw_list = plan.get("shopping_list", [])
    cleaned = [all_names_lower[str(i).lower().strip()] for i in raw_list if str(i).lower().strip() in all_names_lower]
    plan["shopping_list"] = cleaned or [f["name"] for f in db_foods[:6]]

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
    """
    pool = db_foods[:]
    if has_pregnant:
        pool = [f for f in pool if f["pregnancy_safe"]] or pool
    if has_diabetic:
        pool = [f for f in pool if f["diabetes_friendly"]] or pool

    if not pool:
        return {"error": "No suitable foods found in the database for this meal plan.", "days": [], "shopping_list": []}

    fasting_pool = [f for f in pool if f["fasting_safe"]] or pool

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

    def build_meal(grouped: dict[str, list[dict]], used_today: set, category_order: list[str], n: int) -> list[dict]:
        """Pull up to n foods, preferring categories not yet used today, cycling through category_order."""
        picks = []
        cats_cycle = [c for c in category_order if c in grouped]
        if not cats_cycle:
            return picks
        attempts = 0
        i = 0
        while len(picks) < n and attempts < n * len(cats_cycle) + 5:
            cat = cats_cycle[i % len(cats_cycle)]
            candidate = next_from_category(cat, grouped)
            attempts += 1
            i += 1
            if candidate and candidate["name"] not in used_today:
                picks.append(candidate)
                used_today.add(candidate["name"])
        return picks

    # A typical Ethiopian plate centers on grains, then rotates through
    # legumes/meat/dairy_poultry/vegetables/special for the rest.
    primary_order = ["grains", "legumes", "vegetables", "meat", "dairy_poultry", "special", "drinks"]

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
        # from anywhere in the day's pool (still avoiding same-day repeats
        # where possible).
        def top_up(items: list[dict], n: int):
            if len(items) >= n:
                return items
            remaining = [f for foods in grouped.values() for f in foods if f["name"] not in used_today]
            random.shuffle(remaining)
            for f in remaining:
                if len(items) >= n:
                    break
                items.append(f)
                used_today.add(f["name"])
            return items

        b = top_up(b, 2)
        l = top_up(l, 3)
        d = top_up(d, 2)

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

    # Shopping list: pull a few items from each category present, rather than
    # just the first N foods in the raw pool.
    shopping = []
    for cat in primary_order:
        for f in pool_by_cat.get(cat, [])[:2]:
            if f["name"] not in shopping:
                shopping.append(f["name"])
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