import re
from rest_framework import serializers
from .models import EthiopianFood, MealLog, MealLogFood, DailyNutrition


class FoodSerializer(serializers.ModelSerializer):
    """
    Full food record. Safely extracts Amharic and English text slices
    directly from display_name if explicit columns don't exist.
    """
    display_name_html = serializers.SerializerMethodField()
    name_am = serializers.SerializerMethodField()
    name_en = serializers.SerializerMethodField()

    class Meta:
        model = EthiopianFood
        fields = [
            "id", "slug",
            "name_en", "name_am",
            "display_name", "display_name_html",
            "category", "serving_description", "serving_g",
            "calories_kcal", "fiber_g", "protein_g", "iron_mg",
            "glycemic_index",
            "fermentation_score", "prebiotic_score", "inflammatory_index",
            "fasting_safe", "pregnancy_safe", "diabetes_friendly",
            "planner_weekly_safe", "planner_daily_limit",
            "source_citation", "notes", "image_url", "is_active",
        ]

    def _parse_names(self, obj: EthiopianFood):
        # Safely check if fields exist on model to prevent 500 crashes
        raw_en = getattr(obj, 'name_en', '') or ""
        raw_am = getattr(obj, 'name_am', '') or ""
        
        if raw_en and raw_am:
            return str(raw_en).strip(), str(raw_am).strip()

        # Fallback: Extract from "Injera teff  [እንጀራ]" format
        dn = getattr(obj, 'display_name', '') or ""
        if dn and "[" in dn:
            match = re.search(r"([^\[]+)\[([^\]]+)\]", dn)
            if match:
                return match.group(1).strip(), match.group(2).strip()

        return dn.strip(), ""

    def get_name_en(self, obj: EthiopianFood) -> str:
        en, _ = self._parse_names(obj)
        return en

    def get_name_am(self, obj: EthiopianFood) -> str:
        _, am = self._parse_names(obj)
        return am

    def get_display_name_html(self, obj: EthiopianFood) -> str:
        en, am = self._parse_names(obj)
        if am:
            return f"<strong>{am}</strong>&nbsp;&nbsp;<span style='color: #6b7280;'>({en})</span>"
        return en


class FoodMinimalSerializer(serializers.ModelSerializer):
    """
    Lightweight variant used inside dashboards and feed logs.
    Guarantees name blocks are sent down to satisfy front-end layout engines.
    """
    name_en = serializers.SerializerMethodField()
    name_am = serializers.SerializerMethodField()

    class Meta:
        model = EthiopianFood
        fields = [
            "id", "slug", "display_name", "name_en", "name_am",
            "category", "calories_kcal", "fiber_g", "protein_g", "iron_mg",
        ]

    def _parse_names(self, obj: EthiopianFood):
        raw_en = getattr(obj, 'name_en', '') or ""
        raw_am = getattr(obj, 'name_am', '') or ""
        
        if raw_en and raw_am:
            return str(raw_en).strip(), str(raw_am).strip()

        dn = getattr(obj, 'display_name', '') or ""
        if dn and "[" in dn:
            match = re.search(r"([^\[]+)\[([^\]]+)\]", dn)
            if match:
                return match.group(1).strip(), match.group(2).strip()
        return dn.strip(), ""

    def get_name_en(self, obj: EthiopianFood) -> str:
        en, _ = self._parse_names(obj)
        return en

    def get_name_am(self, obj: EthiopianFood) -> str:
        _, am = self._parse_names(obj)
        return am


class MealLogFoodSerializer(serializers.ModelSerializer):
    food = FoodMinimalSerializer(read_only=True)

    class Meta:
        model = MealLogFood
        fields = ["food", "servings"]


class MealLogSerializer(serializers.ModelSerializer):
    foods = MealLogFoodSerializer(source="meallogfood_set", many=True, read_only=True)

    class Meta:
        model = MealLog
        fields = [
            "id", "date", "meal_type", "foods",
            "gut_score", "fiber_g_total", "protein_g_total",
            "iron_mg_total", "fermentation_total", "inflammatory_net",
            "notes", "created_at",
        ]


class MealLogCreateSerializer(serializers.Serializer):
    date = serializers.DateField()
    meal_type = serializers.ChoiceField(choices=MealLog.MEAL_TYPE_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    foods = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
    )


class DailyNutritionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyNutrition
        fields = [
            "date", "gut_score", "wellness_score",
            "fiber_g", "protein_g", "iron_mg",
            "fermentation_total", "inflammatory_net",
            "meal_count", "kuriftu_tip",
        ]