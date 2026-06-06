#ai/engine.py
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Well-Net AI Wellness Engine — powered by Groq + LLaMA
Generates personalised wellness tips, meal plans,
and wellness journey insights.
Food-aware: injects real EPHI 2025 food DB into every prompt.
Dietary-strict: fasting, pregnancy, diabetes rules enforced.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations
import json
from django.conf import settings

try:
    from groq import Groq
    _client = Groq(api_key=settings.GROQ_API_KEY)
    _provider = "groq"
except Exception:
    _client = None
    _provider = None


SYSTEM_PROMPT = """You are Hana, Well-Net's AI wellness coach.
Well-Net is an Ethiopian wellness lifestyle ecosystem — not a medical app.

STRICT RULES — never break these:
1. FASTING MODE: If user is fasting, NEVER suggest meat, dairy (ayib, ergo, milk,
   niter kibbeh, butter), eggs, or any animal products. Only suggest foods explicitly
   marked fasting-safe in the database.
2. PREGNANCY: Never suggest raw meat (kitfo), alcohol (tej, tella), fenugreek (abish),
   gesho, or mitmita. Always prioritise iron-rich foods (gomen, teff, misir wot).
3. DIABETES: Only suggest low-GI foods (GI under 55). Avoid honey, sugar, white bread,
   and high-carb foods.
4. MEAL BALANCE per day:
   - Breakfast: light — porridge, bread, or fermented drink
   - Lunch: main meal — legume or meat stew with injera
   - Dinner: lighter than lunch — soup, vegetables, or small stew
5. WEEKLY VARIETY: Never repeat the same main dish more than twice per week.
6. Always reference foods by exact name from the Well-Net EPHI 2025 database.
7. Never diagnose. Always suggest consulting a professional for medical issues.

Tone: warm, motivating, culturally proud. Like a knowledgeable Ethiopian friend."""


# ── Food context builder ──────────────────────────────────────────────────────

def _get_food_context(
    fasting: bool = False,
    pregnant: bool = False,
    diabetic: bool = False,
    limit: int = 25,
) -> str:
    """
    Pull real foods from EPHI 2025 DB and format for AI context.
    Strictly filters by dietary flags.
    """
    try:
        from foods.models import EthiopianFood
        qs = EthiopianFood.objects.filter(is_active=True)
        if fasting:  qs = qs.filter(fasting_safe=True)
        if pregnant: qs = qs.filter(pregnancy_safe=True)
        if diabetic: qs = qs.filter(diabetes_friendly=True)

        foods = qs.values(
            "name_en", "name_am", "category",
            "fiber_g", "protein_g", "iron_mg",
            "fermentation_score", "fasting_safe",
            "pregnancy_safe", "diabetes_friendly",
            "glycemic_index", "inflammatory_index",
        ).order_by("category")[:limit]

        lines = []
        for f in foods:
            flags = []
            if f["fasting_safe"]:             flags.append("FASTING-SAFE")
            if f["pregnancy_safe"]:           flags.append("pregnancy-safe")
            if f["diabetes_friendly"]:        flags.append("diabetes-friendly")
            if f["fermentation_score"] > 0:   flags.append("fermented")
            if f["inflammatory_index"] <= -1: flags.append("anti-inflammatory")
            if not f["fasting_safe"]:         flags.append("NOT-fasting-safe")

            lines.append(
                f"- {f['name_en']}"
                + (f" ({f['name_am']})" if f["name_am"] else "")
                + f" [{f['category']}]"
                + f" F={f['fiber_g']}g P={f['protein_g']}g Fe={f['iron_mg']}mg"
                + (f" GI={f['glycemic_index']}" if f["glycemic_index"] > 0 else "")
                + (f" | {', '.join(flags)}" if flags else "")
            )

        if not lines:
            return ""

        header = "Well-Net EPHI 2025 verified foods"
        if fasting:
            header += " (FASTING MODE — only fasting-safe foods shown)"
        if pregnant:
            header += " (PREGNANCY MODE)"
        if diabetic:
            header += " (DIABETES MODE — low-GI only)"

        return header + ":\n" + "\n".join(lines)
    except Exception as e:
        print(f"Food context error: {e}")
        return ""


def _build_dietary_rules(profile: dict) -> str:
    """Build strict dietary rules string from user profile."""
    rules = []
    if profile.get("is_fasting_season"):
        rules.append(
            "🚫 FASTING ACTIVE — NEVER suggest: ayib, ergo, tibs, doro wot, kitfo, "
            "dulet, tej, tella, milk, niter kibbeh, butter, eggs, or ANY meat/dairy. "
            "ONLY use foods marked FASTING-SAFE."
        )
    if profile.get("is_pregnant"):
        rules.append(
            "🤰 PREGNANCY — MUST include iron-rich food every day (gomen, teff porridge, "
            "misir wot). NEVER suggest kitfo, raw meat, tej, tella, abish, mitmita, gesho."
        )
    if profile.get("has_diabetes"):
        rules.append(
            "🩸 DIABETES — ONLY low-GI foods (GI < 55). NEVER suggest honey, sugar, "
            "white bread, potatoes, high-carb foods."
        )
    if profile.get("has_anemia"):
        rules.append(
            "💊 ANEMIA — prioritise high-iron foods: gomen (6mg), teff porridge (8mg), "
            "misir wot (4.5mg), dulet if not fasting."
        )
    return "\n".join(rules) if rules else "No special dietary restrictions."


# ── Wellness tips ─────────────────────────────────────────────────────────────

def get_wellness_tips(
    gut_score: int,
    weakest_dimension: str,
    top_foods: list[str],
    profile_context: dict,
    language: str = "en",
) -> dict:
    if not _client or not settings.GROQ_API_KEY:
        return _rule_based_tips(gut_score, weakest_dimension, profile_context)

    food_context = _get_food_context(
        fasting=profile_context.get("is_fasting_season", False),
        pregnant=profile_context.get("is_pregnant", False),
        diabetic=profile_context.get("has_diabetes", False),
        limit=25,
    )

    prompt = _build_tip_prompt(
        gut_score, weakest_dimension, top_foods,
        profile_context, language, food_context,
    )

    try:
        response = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=400,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        )
        raw = response.choices[0].message.content
        return _parse_tip_response(raw)
    except Exception as e:
        print(f"TIPS ERROR: {e}")
        return _rule_based_tips(gut_score, weakest_dimension, profile_context)


# ── Meal plan ─────────────────────────────────────────────────────────────────

def get_meal_plan(
    family_members: list[dict],
    days: int = 7,
    language: str = "en",
) -> dict:
    if not _client or not settings.GROQ_API_KEY:
        return {"error": "AI service not configured"}

    all_conditions = []
    for m in family_members:
        all_conditions.extend(m.get("conditions", []))

    is_fasting  = "fasting"  in all_conditions or any(
        m.get("diet_type") == "fasting" for m in family_members
    )
    is_pregnant = "pregnant" in all_conditions
    is_diabetic = "diabetes" in all_conditions

    food_context = _get_food_context(
        fasting=is_fasting,
        pregnant=is_pregnant,
        diabetic=is_diabetic,
        limit=35,
    )

    members_str    = json.dumps(family_members, indent=2)
    dietary_rules  = _build_dietary_rules({
        "is_fasting_season": is_fasting,
        "is_pregnant":       is_pregnant,
        "has_diabetes":      is_diabetic,
    })

    prompt = f"""Create a {days}-day Ethiopian meal plan for this family:
{members_str}

DIETARY RULES — strictly follow:
{dietary_rules}

{food_context}

BALANCE REQUIREMENTS:
- Breakfast: light meal — teff porridge, bread, or light fermented drink
- Lunch: main meal — legume or meat stew + injera (most calories here)
- Dinner: lighter — soup, vegetable stew, or small portion
- Each day must include: 1 fermented food + 1 legume + 1 vegetable
- Never repeat the same main dish more than TWICE in {days} days
- Wednesday and Friday: use ONLY fasting-safe foods if any member is fasting
- Pregnant members: must have iron-rich food (gomen, teff, misir) every day

Format as JSON only:
{{
  "days": [
    {{
      "day": 1,
      "day_name": "Monday",
      "meals": {{
        "breakfast": {{"foods": ["food name"], "notes": "short gut health tip"}},
        "lunch":     {{"foods": ["food name", "food name"], "notes": "short tip"}},
        "dinner":    {{"foods": ["food name"], "notes": "short tip"}}
      }}
    }}
  ],
  "shopping_list": ["item 1", "item 2"]
}}
Respond with ONLY the JSON, no extra text."""

    try:
        response = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=2000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        )
        raw   = response.choices[0].message.content
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception as e:
        print(f"MEAL PLAN ERROR: {e}")
        return {"error": "Could not generate meal plan. Please try again."}


# ── Wellness journey feed ─────────────────────────────────────────────────────

def get_wellness_journey_feed(
    gut_score: int,
    weekly_avg: float,
    streak_days: int,
    profile: dict,
) -> list[dict]:
    if not _client or not settings.GROQ_API_KEY:
        return _rule_based_feed(gut_score, weekly_avg, streak_days)

    food_context   = _get_food_context(
        fasting=profile.get("is_fasting_season", False),
        limit=20,
    )
    dietary_rules  = _build_dietary_rules(profile)

    prompt = f"""Generate a wellness journey feed for this user:
- Today's gut score: {gut_score}/100
- Weekly average: {weekly_avg}/100
- Wellness streak: {streak_days} days
- Primary goal: {profile.get('primary_goal', 'general wellness')}
- Is fasting: {profile.get('is_fasting_season', False)}
- Kuriftu guest: {profile.get('kuriftu_guest', False)}

DIETARY RULES:
{dietary_rules}

{food_context}

Create exactly 4 feed cards. Each food recommendation MUST respect dietary rules above.
Return as JSON array:
[
  {{
    "type": "insight",
    "title": "",
    "body": "",
    "cta_label": "",
    "cta_action": "",
    "color": "teal"
  }}
]

- type: insight | tip | retreat | challenge | milestone
- color: teal | amber | purple | green
- cta_action: "book_kuriftu" | "log_meal" | "view_experts" | null
- One card MUST be type "retreat" — reference a real Kuriftu experience
  (yoga, Mystic Nights sound healing, Boston Day Spa, gut reset retreat)
- One card MUST be type "tip" with a specific food from the database
- Body text max 80 words per card
Respond with ONLY the JSON array, no extra text."""

    try:
        response = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=600,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        )
        raw   = response.choices[0].message.content
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception as e:
        print(f"FEED ERROR: {e}")
        return _rule_based_feed(gut_score, weekly_avg, streak_days)


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_tip_prompt(
    score, weakness, top_foods, profile, language, food_context=""
):
    lang_note = (
        "Respond in Amharic with English in brackets."
        if language == "am" else "Respond in English."
    )
    dietary_rules = _build_dietary_rules(profile)

    return f"""User gut score: {score}/100
Weakest dimension: {weakness}
Foods eaten today: {', '.join(top_foods) if top_foods else 'none logged yet'}
{lang_note}

DIETARY RULES — follow strictly:
{dietary_rules}

{food_context}

Give exactly 3 wellness tips. Each tip MUST:
- Reference a specific food from the Well-Net database above
- Strictly respect ALL dietary rules
- Address weakest dimension ({weakness}) in at least one tip

Return as JSON only:
{{
  "wellness_message": "One warm sentence acknowledging their score",
  "tips": [
    {{"title": "", "body": "", "icon": "leaf|heart|zap|star", "color": "teal|amber|purple"}},
    {{"title": "", "body": "", "icon": "...", "color": "..."}},
    {{"title": "", "body": "", "icon": "...", "color": "..."}}
  ]
}}
Respond with ONLY the JSON, no extra text."""


# ── Response parser ───────────────────────────────────────────────────────────

def _parse_tip_response(raw: str) -> dict:
    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception:
        return {
            "wellness_message": "You're on your wellness journey — every meal counts.",
            "tips": [
                {
                    "title": "Keep going",
                    "body":  raw[:200],
                    "icon":  "leaf",
                    "color": "teal",
                }
            ],
        }


# ── Rule-based fallbacks ──────────────────────────────────────────────────────

def _rule_based_tips(score: int, weakness: str, profile: dict) -> dict:
    is_fasting = profile.get("is_fasting_season", False)

    base = {
        "fiber": {
            "title": "Boost your fiber",
            "body":  "Add misir wot or shiro to your next meal — Ethiopian legumes are prebiotic powerhouses."
                     if not is_fasting else
                     "Add misir wot or kik alicha — excellent fasting-safe fiber sources.",
            "icon":  "leaf", "color": "teal",
        },
        "fermentation": {
            "title": "Add fermented foods",
            "body":  "Injera's natural fermentation adds probiotics your gut loves."
                     if is_fasting else
                     "Injera, ergo (yogurt), or ayib add natural probiotics your gut bacteria love.",
            "icon":  "heart", "color": "purple",
        },
        "inflammation": {
            "title": "Cool inflammation",
            "body":  "Gomen and shiro are strongly anti-inflammatory. Berbere spice is your friend.",
            "icon":  "zap", "color": "amber",
        },
        "protein": {
            "title": "Protein boost",
            "body":  "Add kik alicha or misir wot for plant protein today."
                     if is_fasting else
                     "Add kik alicha or doro wot to hit your protein target.",
            "icon":  "star", "color": "teal",
        },
    }
    primary_tip = base.get(weakness, base["fiber"])
    label = "Great" if score >= 80 else "Good" if score >= 65 else "Keep improving"
    return {
        "wellness_message": f"{label} work! Your score of {score} shows real progress.",
        "tips": [
            primary_tip,
            {
                "title": "Kuriftu moment",
                "body":  "Your wellness journey aligns with Kuriftu's wellness retreats — a gut reset experience awaits.",
                "icon":  "star", "color": "teal",
            },
            {
                "title": "Consistency wins",
                "body":  "Log your meals daily — users who log consistently improve their score by 18 points in 2 weeks.",
                "icon":  "zap", "color": "amber",
            },
        ],
    }


def _rule_based_feed(score: int, weekly_avg: float, streak: int) -> list[dict]:
    return [
        {
            "type":       "insight",
            "title":      f"Your score: {score}/100",
            "body":       f"Weekly average: {weekly_avg}. {'Trending up! 🎉' if score > weekly_avg else 'Keep going — consistency is everything.'}",
            "cta_label":  None,
            "cta_action": None,
            "color":      "teal",
        },
        {
            "type":       "tip",
            "title":      "Today's wellness tip",
            "body":       "Start your morning with teff porridge (genfo) — 8mg iron and 7g fiber per bowl. One of the most nutritious breakfasts in the world.",
            "cta_label":  "Log breakfast",
            "cta_action": "log_meal",
            "color":      "amber",
        },
        {
            "type":       "retreat",
            "title":      "Kuriftu Wellness Experience",
            "body":       "Kuriftu's Mystic Nights sound healing pairs perfectly with your wellness journey. Guests receive a Gut Health Passport scan at check-in.",
            "cta_label":  "Learn more",
            "cta_action": "book_kuriftu",
            "color":      "purple",
        },
        {
            "type":       "challenge",
            "title":      f"{streak}-day streak! 🔥",
            "body":       f"You've logged meals for {streak} days. Add misir wot today — GI of 19 keeps your blood sugar stable all afternoon.",
            "cta_label":  "Log now",
            "cta_action": "log_meal",
            "color":      "green",
        },
    ]
