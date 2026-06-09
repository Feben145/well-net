"""
foods/models.py
━━━━━━━━━━━━━━━
Ethiopian food database + meal logging.

Single source: all food data comes from the EPHI 2025 PDF via
  python manage.py parse_ephi_pdf [--update]

Never seed from any other file.
"""
from django.db import models
from django.contrib.auth import get_user_model
from core.base import TimeStampedModel

User = get_user_model()


class EthiopianFood(TimeStampedModel):
    """
    Master food record — seeded exclusively from parse_ephi_pdf.py.
    All nutritional values are per 100 g edible portion (EPHI standard).

    Source: EPHI Food Composition Table 2025.
    """

    SOURCE_CHOICES = [
        ("ephi",     "EPHI Ethiopia 2025"),   # ← primary / only source
        ("fao",      "FAO"),
        ("usda",     "USDA"),
        ("pmc",      "PMC Research"),
        ("heritage", "Heritage Nutrition"),
    ]

    CATEGORY_CHOICES = [
        ("grains",     "Grains & Breads"),
        ("legumes",    "Legumes & Pulses"),
        ("meat",       "Meat & Poultry"),
        ("dairy",      "Dairy & Fermented"),
        ("vegetables", "Vegetables"),
        ("drinks",     "Drinks"),
        ("special",    "Special Ingredients"),
    ]

    # ── Identity ──────────────────────────────────────────────────────────────
    slug         = models.SlugField(unique=True)
    name_en      = models.CharField(max_length=200)   # cleaned, no commas
    name_am      = models.CharField(max_length=200, blank=True)   # "እንጀራ"
    # display_name is the pre-formatted string shown to users:
    #   "Injera teff  [እንጀራ]"
    # The Amharic part inside [ ] is styled bold by the frontend/serializer.
    display_name = models.CharField(max_length=300, blank=True)

    category            = models.CharField(max_length=200, choices=CATEGORY_CHOICES)
    serving_description = models.CharField(max_length=200)   # "Per 100g edible portion"
    serving_g           = models.FloatField()
    source              = models.CharField(max_length=200, choices=SOURCE_CHOICES, default="ephi")

    # ── Nutritional data (per 100 g) ──────────────────────────────────────────
    calories_kcal = models.FloatField(default=0)
    fiber_g       = models.FloatField(default=0)
    protein_g     = models.FloatField(default=0)
    iron_mg       = models.FloatField(default=0)
    fat_g         = models.FloatField(
    default=0,
    help_text="Total fat per 100g edible portion (EPHI 2025)."
   )
    glycemic_index = models.IntegerField(default=0)

    # ── Gut health scores (0–3 scale) ─────────────────────────────────────────
    fermentation_score  = models.IntegerField(default=0)  # 0=none  3=high probiotic
    prebiotic_score     = models.IntegerField(default=0)  # 0=none  3=excellent
    inflammatory_index  = models.IntegerField(default=0)  # -2=anti-inflam  +2=pro-inflam

    # ── Dietary flags ─────────────────────────────────────────────────────────
    fasting_safe      = models.BooleanField(default=False)   # Ethiopian Orthodox fasting
    pregnancy_safe    = models.BooleanField(default=False)
    diabetes_friendly = models.BooleanField(default=False)

    # ── Weekly meal planner safety ────────────────────────────────────────────
    # planner_weekly_safe=False → this food should appear ≤1 × per week
    #   (strong flavour, high processing, or alcohol-adjacent)
    planner_weekly_safe  = models.BooleanField(default=True)
    # planner_daily_limit → max servings of this *category* in one day's meals
    planner_daily_limit  = models.IntegerField(default=2)

    # ── Meta ──────────────────────────────────────────────────────────────────
    source_citation = models.CharField(max_length=200, blank=True)
    notes           = models.TextField(blank=True)
    image_url       = models.URLField(blank=True)
    is_active       = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name_en"]

    def __str__(self):
        if self.name_am:
            return f"{self.name_en} [{self.name_am}] ({self.category})"
        return f"{self.name_en} ({self.category})"

    def get_display_name(self) -> str:
        """
        Return the user-facing name.
        If display_name was pre-built by the parser use it,
        otherwise build it on the fly.
        """
        if self.display_name:
            return self.display_name
        if self.name_am:
            return f"{self.name_en}  [{self.name_am}]"
        return self.name_en


# ── Meal Logging ──────────────────────────────────────────────────────────────

class MealLog(TimeStampedModel):
    """
    One meal entry — user + list of foods eaten.
    Gut score is computed and cached here after creation by the scoring engine.
    """
    MEAL_TYPE_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch",     "Lunch"),
        ("dinner",    "Dinner"),
        ("snack",     "Snack"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="meal_logs"
    )
    family_member = models.ForeignKey(
        "users.FamilyMember",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="meal_logs",
        help_text="Set if logging for a family member, not the user themselves.",
    )

    date      = models.DateField()
    meal_type = models.CharField(max_length=200, choices=MEAL_TYPE_CHOICES)
    foods     = models.ManyToManyField(EthiopianFood, through="MealLogFood")

    # Computed by scoring engine after save
    gut_score          = models.IntegerField(default=0)
    fiber_g_total      = models.FloatField(default=0)
    protein_g_total    = models.FloatField(default=0)
    iron_mg_total      = models.FloatField(default=0)
    fermentation_total = models.IntegerField(default=0)
    inflammatory_net   = models.IntegerField(default=0)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.date} {self.meal_type}"


class MealLogFood(models.Model):
    """Through table: MealLog ↔ EthiopianFood with portion multiplier."""
    meal_log = models.ForeignKey(MealLog, on_delete=models.CASCADE)
    food     = models.ForeignKey(EthiopianFood, on_delete=models.CASCADE)
    servings = models.FloatField(default=1.0)   # 0.5 = half, 2.0 = double

    class Meta:
        unique_together = ("meal_log", "food")


class DailyNutrition(TimeStampedModel):
    """
    Aggregated daily nutrition summary — one record per user per day.
    Computed by the scoring engine. Used for weekly trend charts.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="daily_nutrition"
    )
    date = models.DateField()

    gut_score          = models.IntegerField(default=0)
    wellness_score     = models.IntegerField(default=0)
    fiber_g            = models.FloatField(default=0)
    protein_g          = models.FloatField(default=0)
    iron_mg            = models.FloatField(default=0)
    fermentation_total = models.IntegerField(default=0)
    inflammatory_net   = models.IntegerField(default=0)
    meal_count         = models.IntegerField(default=0)

    kuriftu_tip = models.TextField(blank=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.email} — {self.date} score={self.gut_score}"
