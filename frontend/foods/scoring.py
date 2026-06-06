"""
foods/scoring.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Well-Net Gut Health + Wellness Scoring Engine

Formula (scientifically grounded — sources in food_data.py):
  gut_score = fiber(40%) + fermentation(30%) + inflammation(20%) + protein(10%)

Profile overrides applied for: pregnancy, diabetes, fasting, age.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ── Score thresholds ──────────────────────────────────────────────────────────
SCORE_LABELS = [
    (85, "Excellent", "#1D9E75"),
    (70, "Great",     "#5DCAA5"),
    (55, "Good",      "#9FE1CB"),
    (40, "Fair",      "#EF9F27"),
    (0,  "Needs attention", "#E24B4A"),
]


def score_label(score: int) -> tuple[str, str]:
    """Return (label, color) for a given score 0–100."""
    for threshold, label, color in SCORE_LABELS:
        if score >= threshold:
            return label, color
    return "Needs attention", "#E24B4A"


# ── Input dataclasses ─────────────────────────────────────────────────────────

@dataclass
class FoodItem:
    """Minimal food values needed by the engine."""
    slug: str
    fiber_g: float
    protein_g: float
    iron_mg: float
    fermentation_score: int       # 0–3
    inflammatory_index: int       # -2 to +2
    prebiotic_score: int          # 0–3
    glycemic_index: int = 50
    servings: float = 1.0         # portion multiplier


@dataclass
class UserContext:
    """Profile overrides that adjust scoring weights."""
    is_pregnant: bool = False
    has_diabetes: bool = False
    has_anemia: bool = False
    is_fasting: bool = False
    age: Optional[int] = None
    primary_goal: str = "general"


@dataclass
class ScoreResult:
    """Full scoring output returned to API and frontend."""
    gut_score: int
    fiber_g: float
    protein_g: float
    iron_mg: float
    fermentation_total: float
    inflammatory_net: float

    # Sub-scores 0–100 (shown as bars in UI)
    fiber_sub: int
    fermentation_sub: int
    inflammation_sub: int
    protein_sub: int

    # Labels
    label: str
    color: str

    # Alerts (list of dicts with type + message)
    alerts: list[dict] = field(default_factory=list)

    # Kuriftu recommendation driven by score range
    kuriftu_tip: str = ""

    # AI tip inputs (passed to ai/ engine)
    top_foods: list[str] = field(default_factory=list)
    weakest_dimension: str = ""


# ── Main scoring function ─────────────────────────────────────────────────────

def compute_gut_score(
    foods: list[FoodItem],
    context: Optional[UserContext] = None,
) -> ScoreResult:
    """
    Compute gut health score for a list of food items.

    Weights (base):
        fiber:         40%  — per FAO/PMC fiber recommendations
        fermentation:  30%  — probiotic benefit from injera, tej, ergo
        inflammation:  20%  — berbere, legumes reduce; red meat raises
        protein:       10%  — complete daily protein target

    Profile overrides:
        pregnancy  → iron weight increases, raw meat penalty added
        diabetes   → glycemic index factored into fiber sub-score
        anemia     → iron weight increases to 15%
        fasting    → meat items silently skipped in scoring (already logged)
    """
    ctx = context or UserContext()

    if not foods:
        return ScoreResult(
            gut_score=0, fiber_g=0, protein_g=0, iron_mg=0,
            fermentation_total=0, inflammatory_net=0,
            fiber_sub=0, fermentation_sub=0, inflammation_sub=0, protein_sub=0,
            label="No foods logged", color="#E24B4A",
        )

    # ── 1. Aggregate totals (apply serving multiplier) ────────────────────────
    fiber       = sum(f.fiber_g * f.servings for f in foods)
    protein     = sum(f.protein_g * f.servings for f in foods)
    iron        = sum(f.iron_mg * f.servings for f in foods)
    ferm        = sum(f.fermentation_score * f.servings for f in foods)
    inflam      = sum(f.inflammatory_index * f.servings for f in foods)
    prebiotic   = sum(f.prebiotic_score * f.servings for f in foods)

    # ── 2. Sub-scores (normalise to 0–100) ────────────────────────────────────
    # Targets: fiber 25g/day, ferm 6 per meal, protein 50g/day
    fiber_sub  = min(int((fiber / 25) * 100), 100)
    ferm_sub   = min(int((ferm / 6) * 100), 100)
    prot_sub   = min(int((protein / 50) * 100), 100)

    # Inflammation: net -4 → 100, net +4 → 0
    inf_sub = max(0, min(100, int((4 - inflam) / 8 * 100)))

    # Diabetes override: penalise high-GI meals
    if ctx.has_diabetes:
        avg_gi = sum(f.glycemic_index for f in foods) / len(foods)
        if avg_gi > 60:
            fiber_sub = max(0, fiber_sub - 20)

    # ── 3. Weighted composite score ───────────────────────────────────────────
    weights = _get_weights(ctx)
    gut_score = int(
        fiber_sub  * weights["fiber"] +
        ferm_sub   * weights["ferm"] +
        inf_sub    * weights["inflam"] +
        prot_sub   * weights["protein"]
    )
    gut_score = max(0, min(100, gut_score))

    # ── 4. Alerts ─────────────────────────────────────────────────────────────
    alerts = _build_alerts(fiber, iron, ferm, inflam, ctx)

    # ── 5. Kuriftu tip ────────────────────────────────────────────────────────
    kuriftu_tip = _kuriftu_tip(gut_score, ctx)

    # ── 6. Weakest dimension (for AI prompt) ─────────────────────────────────
    dims = {
        "fiber": fiber_sub,
        "fermentation": ferm_sub,
        "inflammation": inf_sub,
        "protein": prot_sub,
    }
    weakest = min(dims, key=dims.get)

    label, color = score_label(gut_score)

    return ScoreResult(
        gut_score=gut_score,
        fiber_g=round(fiber, 1),
        protein_g=round(protein, 1),
        iron_mg=round(iron, 1),
        fermentation_total=round(ferm, 1),
        inflammatory_net=round(inflam, 1),
        fiber_sub=fiber_sub,
        fermentation_sub=ferm_sub,
        inflammation_sub=inf_sub,
        protein_sub=prot_sub,
        label=label,
        color=color,
        alerts=alerts,
        kuriftu_tip=kuriftu_tip,
        top_foods=[f.slug for f in sorted(foods, key=lambda x: x.fiber_g + x.fermentation_score, reverse=True)[:3]],
        weakest_dimension=weakest,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_weights(ctx: UserContext) -> dict:
    """Adjust scoring weights based on user profile."""
    base = {"fiber": 0.40, "ferm": 0.30, "inflam": 0.20, "protein": 0.10}

    if ctx.is_pregnant:
        # Iron + anti-inflammation more critical in pregnancy
        base["inflam"] += 0.05
        base["protein"] += 0.05
        base["fiber"] -= 0.05
        base["ferm"] -= 0.05

    if ctx.has_anemia:
        # We don't score iron directly, but flag it in alerts
        pass  # handled via alerts

    if ctx.primary_goal == "gut_health":
        base["ferm"] += 0.05
        base["fiber"] += 0.05
        base["protein"] -= 0.05
        base["inflam"] -= 0.05

    if ctx.primary_goal == "energy":
        base["protein"] += 0.10
        base["fiber"] -= 0.05
        base["ferm"] -= 0.05

    # Normalise to sum=1.0
    total = sum(base.values())
    return {k: v / total for k, v in base.items()}


def _build_alerts(fiber, iron, ferm, inflam, ctx: UserContext) -> list[dict]:
    """Generate contextual health alerts."""
    alerts = []

    if ctx.is_pregnant and iron < 2.5:
        alerts.append({
            "type": "warning",
            "icon": "iron",
            "message": "Iron is low — add gomen (collard greens) or abish (fenugreek) today.",
        })

    if ctx.has_anemia and iron < 3.0:
        alerts.append({
            "type": "warning",
            "icon": "iron",
            "message": "Iron target not met — try misir wot or gomen.",
        })

    if fiber < 8:
        alerts.append({
            "type": "tip",
            "icon": "fiber",
            "message": "Fiber is low — add injera or misir wot to your next meal.",
        })

    if ferm == 0:
        alerts.append({
            "type": "tip",
            "icon": "fermentation",
            "message": "No fermented foods today — add injera, ergo, or ayib.",
        })

    if inflam > 2:
        alerts.append({
            "type": "caution",
            "icon": "inflammation",
            "message": "High inflammation today — balance with shiro or gomen tomorrow.",
        })

    return alerts


def _kuriftu_tip(score: int, ctx: UserContext) -> str:
    """Match gut score to a Kuriftu wellness experience."""
    if ctx.is_pregnant:
        return "Kuriftu's Prenatal Wellness package includes gentle yoga + iron-rich meal plans."
    if score >= 80:
        return "Your score qualifies for Kuriftu's Probiotic Rejuvenation Retreat — celebrate your gut health."
    if score >= 65:
        return "Book the Kuriftu Herbal Harmony spa — perfect for your current wellness level."
    if score >= 50:
        return "Kuriftu's Gut Reset Weekend (off-peak Tuesday–Thursday) — 30% discount available now."
    return "Kuriftu's Intensive Wellness Detox program is designed for a full gut reset. Off-peak slots open."
