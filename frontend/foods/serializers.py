"""
foods/serializers.py
━━━━━━━━━━━━━━━━━━━━
All food data originates from parse_ephi_pdf.py (EPHI 2025).

display_name format:  "Injera teff  [እንጀራ]"
  → the frontend should render the bracketed Amharic bold.
  → the serializer also ships display_name_html for web consumers.
"""
from rest_framework import serializers
from .models import EthiopianFood, MealLog, MealLogFood, DailyNutrition


class FoodSerializer(serializers.ModelSerializer):
    """
    Full food record.  Two name fields are provided:
      display_name      — plain text  "Injera teff  [እንጀራ]"
      display_name_html — HTML  "Injera teff  <strong>እንጀራ</strong>"
    """
    display_name_html = serializers.SerializerMethodField()

    class Meta:
        model  = EthiopianFood
        fields = [
            "id", "slug",
            "name_en", "name_am",
            "display_name", "display_name_html",   # ← Amharic bold
            "category", "serving_description", "serving_g",
            "calories_kcal", "fiber_g", "protein_g", "iron_mg",
            "glycemic_index",
            "fermentation_score", "prebiotic_score", "inflammatory_index",
            "fasting_safe", "pregnancy_safe", "diabetes_friendly",
            "planner_weekly_safe", "planner_daily_limit",             # ← planner
            "source_citation", "notes", "image_url", "is_active",
        ]

    def get_display_name_html(self, obj: EthiopianFood) -> str:
        """
        Wrap the Amharic name in <strong> for web rendering.
        Plain English name stays unstyled.
        """
        if obj.name_am:
            return (
                f"{obj.name_en}&nbsp;&nbsp;"
                f"<strong>{obj.name_am}</strong>"
            )
        return obj.name_en


class FoodMinimalSerializer(serializers.ModelSerializer):
    """Lightweight variant used inside MealLog and planner responses."""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model  = EthiopianFood
        fields = [
            "id", "slug", "display_name",
            "category", "calories_kcal",
            "fiber_g", "protein_g", "iron_mg",
        ]

    def get_display_name(self, obj: EthiopianFood) -> str:
        return obj.get_display_name()


class MealLogFoodSerializer(serializers.ModelSerializer):
    food = FoodMinimalSerializer(read_only=True)

    class Meta:
        model  = MealLogFood
        fields = ["food", "servings"]


class MealLogSerializer(serializers.ModelSerializer):
    foods = MealLogFoodSerializer(source="meallogfood_set", many=True, read_only=True)

    class Meta:
        model  = MealLog
        fields = [
            "id", "date", "meal_type", "foods",
            "gut_score", "fiber_g_total", "protein_g_total",
            "iron_mg_total", "fermentation_total", "inflammatory_net",
            "notes", "created_at",
        ]


class MealLogCreateSerializer(serializers.Serializer):
    date      = serializers.DateField()
    meal_type = serializers.ChoiceField(choices=MealLog.MEAL_TYPE_CHOICES)
    notes     = serializers.CharField(required=False, allow_blank=True)
    foods     = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
    )


class DailyNutritionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DailyNutrition
        fields = [
            "date", "gut_score", "wellness_score",
            "fiber_g", "protein_g", "iron_mg",
            "fermentation_total", "inflammatory_net",
            "meal_count", "kuriftu_tip",
        ]
