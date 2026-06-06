"""
foods/management/commands/parse_ephi_pdf.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Single source of truth for ALL food data in the app.
Parses the EPHI Food Composition Table 2025 PDF and
imports foods into the EthiopianFood model.

Used by:
  - Food page  (FoodListView / FoodDetailView)
  - AI recommendations  (wellness/views.py → get_ai_recommendations)
  - Nutrition guide     (wellness/views.py → nutrition_guide)
  - Weekly meal planner (wellness/views.py → weekly_meal_plan)
"""

from __future__ import annotations
import re
import unicodedata
from django.core.management.base import BaseCommand
from foods.models import EthiopianFood
from django.db import models

PDF_PATH = "foods/data/ephi.pdf"

GROUP_MAP = {
    "01": "grains",
    "02": "grains",
    "03": "legumes",
    "04": "vegetables",
    "05": "special",
    "06": "meat",
    "07": "meat",
    "08": "dairy",
    "09": "dairy",
    "10": "special",
    "11": "drinks",
    "12": "special",
    "13": "special",
    "14": "grains",
    "15": "legumes",
    "16": "meat",
    "17": "vegetables",
}

FASTING_SAFE_GROUPS = {"03", "04", "11", "12"}


# ─────────────────────────────────────────────
# Name cleaning helpers
# ─────────────────────────────────────────────

def clean_food_name(name: str) -> str:
    """
    Remove commas from food names.
    In the EPHI PDF a single food is sometimes written as:
      "Injera, teff"  →  should be  "Injera teff"
    Commas make one food look like a list of multiple items,
    which breaks the weekly meal planner and display cards.
    """
    name = name.replace(",", " ")
    name = re.sub(r"\s{2,}", " ", name)
    return name.strip()


def format_display_name(name_en: str, name_am: str) -> str:
    """
    Return a display string that shows the Amharic name
    in bold-capable bracket notation:
      "Injera teff  [እንጀራ]"
    The bracket form is safe for both plain text and HTML
    (frontend can style [ame] as bold via CSS).
    """
    name_en = clean_food_name(name_en)
    if name_am and name_am.strip():
        return f"{name_en}  [{name_am.strip()}]"
    return name_en


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:90]


def safe_float(val, default=0.0):
    if not val:
        return default
    val = str(val).strip().replace("[", "").replace("]", "")
    if val in ("", "-", "—", "tr", "oa", "na", "NA"):
        return default
    try:
        return float(val)
    except ValueError:
        return default


# ─────────────────────────────────────────────
# Scoring logic
# ─────────────────────────────────────────────

def compute_fermentation_score(name_en: str, name_am: str) -> int:
    name = (name_en + " " + name_am).lower()
    if any(w in name for w in ["injera", "ergo", "tej", "tella", "kocho",
                                "enset", "borde", "shameta"]):
        return 3
    if any(w in name for w in ["ayib", "yogurt", "ferment", "soured", "kultured"]):
        return 2
    if any(w in name for w in ["dabo", "bread", "genfo", "porridge"]):
        return 1
    return 0


def compute_prebiotic_score(fiber_g: float, name_en: str) -> int:
    name = name_en.lower()
    if any(w in name for w in ["lentil", "chickpea", "pea", "bean", "misir",
                                "shiro", "barley", "oat"]):
        return 3
    if fiber_g >= 6:
        return 3
    if fiber_g >= 3:
        return 2
    if fiber_g >= 1:
        return 1
    return 0


def compute_inflammatory_index(name_en: str, fat_g: float, fiber_g: float) -> int:
    name = name_en.lower()
    if any(w in name for w in ["berbere", "turmeric", "ginger", "garlic",
                                "collard", "cabbage", "kale", "spice"]):
        return -2
    if any(w in name for w in ["vegetable", "legume", "lentil", "bean",
                                "pea", "green", "leaf"]):
        return -1
    if any(w in name for w in ["organ", "liver", "tripe", "processed",
                                "fried", "deep", "sausage"]):
        return 2
    if fat_g > 20:
        return 1
    if fiber_g > 5:
        return -1
    return 0


def compute_glycemic_index(name_en: str, cho_g: float) -> int:
    name = name_en.lower()
    known = {
        "injera": 35, "teff": 35, "lentil": 19, "misir": 19,
        "chickpea": 28, "shiro": 28, "split pea": 22, "barley": 28,
        "potato": 55, "sweet potato": 50, "bread white": 68,
        "bread whole": 51, "rice": 72, "maize": 52, "sorghum": 55,
        "banana": 51, "mango": 51, "honey": 55, "sugar": 65,
        "milk": 35, "yogurt": 35, "oat": 55, "wheat": 60,
    }
    for key, gi in known.items():
        if key in name:
            return gi
    if cho_g == 0:
        return 0
    if cho_g < 10:
        return 15
    if cho_g < 30:
        return 40
    return 55


def is_pregnancy_safe(name_en: str) -> bool:
    name = name_en.lower()
    unsafe = ["alcohol", "tej", "tella", "raw meat", "kitfo",
              "raw fish", "fenugreek", "abish", "gesho", "mitmita"]
    return not any(w in name for w in unsafe)


def is_diabetes_friendly(gi: int, cho_g: float) -> bool:
    if gi == 0:
        return True
    return gi <= 55 and cho_g <= 40


# ─────────────────────────────────────────────
# Weekly meal planner safety helpers
# ─────────────────────────────────────────────

# Foods that are nutritionally similar enough that serving them
# in the same day creates redundancy or macro imbalance.
# Keys are category pairs; values are max occurrences per day.
DAILY_CATEGORY_LIMITS = {
    "grains":     2,   # max 2 grain-based items per day
    "meat":       2,   # max 2 meat/poultry per day
    "legumes":    3,
    "dairy":      2,
    "vegetables": 4,
    "drinks":     2,
    "special":    2,
}

# These foods should not appear more than once per week in a plan
# (strong flavour, high processing, or alcohol risk)
WEEKLY_LIMIT_ONE = {
    "tej", "tella", "kitfo", "raw", "organ", "liver", "tripe",
    "sausage", "processed",
}

def is_planner_safe_weekly(name_en: str) -> bool:
    """Return False for foods that should be capped to ≤1/week."""
    name = name_en.lower()
    return not any(w in name for w in WEEKLY_LIMIT_ONE)

def planner_daily_limit(category: str) -> int:
    """Return how many times a category may appear in one day's meals."""
    return DAILY_CATEGORY_LIMITS.get(category, 2)


# ─────────────────────────────────────────────
# PDF parsing
# ─────────────────────────────────────────────

def parse_ephi_pdf(start_page: int = 44, end_page: int = 390) -> list[dict]:
    """
    Parse the EPHI PDF and return a list of food dicts ready to
    be bulk-inserted into EthiopianFood.

    Each dict includes:
      - slug, name_en, name_am, display_name  (cleaned, no commas)
      - category, serving_description, serving_g
      - calories_kcal, fiber_g, protein_g, iron_mg
      - glycemic_index, fermentation_score, prebiotic_score,
        inflammatory_index
      - fasting_safe, pregnancy_safe, diabetes_friendly
      - planner_weekly_safe, planner_daily_limit  ← new planner fields
      - source_citation, notes, is_active, source
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pip install pdfplumber --break-system-packages")

    part1: dict[str, dict] = {}
    iron_map: dict[str, float] = {}

    with pdfplumber.open(PDF_PATH) as pdf:
        end = min(end_page, len(pdf.pages))

        for page_num in range(start_page, end):
            text = pdf.pages[page_num].extract_text()
            if not text:
                continue

            lines = text.split("\n")
            in_part2 = False

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if "(2/5)" in line or (
                    "calcium" in line.lower() and "iron" in line.lower()
                ):
                    in_part2 = True
                    continue

                if re.search(r"\([3-5]/5\)", line):
                    in_part2 = False
                    continue

                m = re.match(r"^(\d{6})\s+(.+)", line)
                if not m:
                    continue

                code = m.group(1)
                rest = m.group(2).strip()
                group = code[:2]

                if in_part2:
                    nums = re.findall(r"[\d.]+", rest)
                    if len(nums) >= 2:
                        iron_map[code] = safe_float(nums[1])
                else:
                    kcal_m = re.search(r"\d+\((\d+)\)", rest)
                    if not kcal_m:
                        continue

                    kcal = float(kcal_m.group(1))
                    after = rest[kcal_m.end():].strip()
                    nums = re.findall(r"[\d.]+", after)
                    floats = [safe_float(n) for n in nums]

                    protein = floats[1] if len(floats) > 1 else 0.0
                    fat     = floats[2] if len(floats) > 2 else 0.0
                    cho     = floats[3] if len(floats) > 3 else 0.0
                    fiber   = floats[4] if len(floats) > 4 else 0.0

                    name_part  = re.split(r"\s+1\.00\s+|\s{3,}", rest)[0].strip()
                    name_split = re.split(r"\s{2,}", name_part)

                    # ── Clean names: strip commas ──────────────────────────
                    raw_name_en = name_split[0].strip()
                    name_en = clean_food_name(
                        re.sub(r"\s+", " ", raw_name_en)
                    )
                    name_am = (
                        re.sub(r"\s+", " ", name_split[1].strip())
                        if len(name_split) > 1
                        else ""
                    )

                    if name_en and kcal >= 10:
                        part1[code] = {
                            "code": code,
                            "group": group,
                            "name_en": name_en,
                            "name_am": name_am,
                            "kcal": kcal,
                            "protein": protein,
                            "fat": fat,
                            "cho": cho,
                            "fiber": fiber,
                        }

    result: list[dict] = []
    seen_slugs: set[str] = set()

    for code, f in part1.items():
        name_en = f["name_en"]
        name_am = f["name_am"]
        group   = f["group"]

        category = GROUP_MAP.get(group, "special")
        kcal     = f["kcal"]
        protein  = f["protein"]
        fat      = f["fat"]
        cho      = f["cho"]
        fiber    = f["fiber"]
        iron     = iron_map.get(code, 0.0)

        gi        = compute_glycemic_index(name_en, cho)
        ferm      = compute_fermentation_score(name_en, name_am)
        prebiotic = compute_prebiotic_score(fiber, name_en)
        inflam    = compute_inflammatory_index(name_en, fat, fiber)
        fasting   = group in FASTING_SAFE_GROUPS
        preg_safe = is_pregnancy_safe(name_en)
        diab_safe = is_diabetes_friendly(gi, cho)

        # ── Display name: Amharic in brackets ─────────────────────────────
        display_name = format_display_name(name_en, name_am)

        # ── Weekly planner safety fields ──────────────────────────────────
        weekly_safe = is_planner_safe_weekly(name_en)
        daily_limit = planner_daily_limit(category)

        slug = slugify(name_en)
        base = slug
        n = 1
        while slug in seen_slugs:
            slug = f"{base}_{n}"
            n += 1
        seen_slugs.add(slug)

        result.append({
            "slug":                slug,
            "name_en":             name_en,
            "name_am":             name_am,
            "display_name":        display_name,
            "category":            category,
            "serving_description": "Per 100g edible portion",
            "serving_g":           100.0,
            "calories_kcal":       kcal,
            "fiber_g":             fiber,
            "protein_g":           protein,
            "iron_mg":             iron,
            "fat_g": fat,
            "glycemic_index":      gi,
            "fermentation_score":  ferm,
            "prebiotic_score":     prebiotic,
            "inflammatory_index":  inflam,
            "fasting_safe":        fasting,
            "pregnancy_safe":      preg_safe,
            "diabetes_friendly":   diab_safe,
            "planner_weekly_safe": weekly_safe,
            "planner_daily_limit": daily_limit,
            "source_citation":     f"EPHI EFCT 2025 (code {code})",
            "notes": (
                f"EPHI 2025 verified. "
                f"{kcal:.1f} kcal  {protein:.1f}g protein  "
                f"{fat:.1f}g fat  {cho:.1f}g CHO  "
                f"{fiber:.1f}g fiber  {iron:.1f}mg iron."
            ),
            "is_active": True,
            "source":    "ephi",
        })

    return result


# ─────────────────────────────────────────────
# Public accessor used by wellness views
# ─────────────────────────────────────────────

def get_foods_queryset(
    *,
    category: str | None = None,
    fasting_safe: bool | None = None,
    pregnancy_safe: bool | None = None,
    diabetes_friendly: bool | None = None,
    planner_weekly_safe: bool | None = None,
    search: str | None = None,
    active_only: bool = True,
):
    """
    Convenience function so wellness views never import seed data —
    they call this instead.  All filtering is sourced from the EPHI
    data that was imported by this management command.
    """
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
            models.Q(name_en__icontains=search) |
            models.Q(name_am__icontains=search) |
            models.Q(display_name__icontains=search)
        )
    return qs.order_by("category", "name_en")


# ─────────────────────────────────────────────
# Django Management Command
# ─────────────────────────────────────────────

class Command(BaseCommand):
    help = "Parse EPHI Food Composition Table 2025 PDF and import into DB"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run",    action="store_true")
        parser.add_argument("--update",     action="store_true")
        parser.add_argument("--start-page", type=int, default=44)
        parser.add_argument("--end-page",   type=int, default=390)
        parser.add_argument("--min-kcal",   type=float, default=10)
        parser.add_argument(
            "--purge-old",
            action="store_true",
            help=(
                "Deactivate (is_active=False) every EthiopianFood record whose "
                "source != 'ephi' before importing.  Use this once to clean out "
                "any legacy seed data that was imported before parse_ephi_pdf "
                "became the single source of truth.  Safe to run repeatedly."
            ),
        )

    def handle(self, *args, **options):
        dry_run   = options["dry_run"]
        update    = options["update"]
        min_kcal  = options["min_kcal"]
        purge_old = options["purge_old"]

        # ── Step 0: deactivate legacy non-EPHI records ────────────────────────
        if purge_old and not dry_run:
            old_qs = EthiopianFood.objects.exclude(source="ephi").filter(is_active=True)
            count  = old_qs.count()
            if count:
                old_qs.update(is_active=False)
                self.stdout.write(
                    self.style.WARNING(
                        f"Deactivated {count} non-EPHI records "
                        f"(source != 'ephi').  They are kept in the DB but "
                        f"hidden from all API responses."
                    )
                )
            else:
                self.stdout.write("No non-EPHI records to deactivate.")

        self.stdout.write("Parsing EPHI PDF …")

        foods = parse_ephi_pdf(options["start_page"], options["end_page"])
        foods = [f for f in foods if f["calories_kcal"] >= min_kcal]

        self.stdout.write(f"Found {len(foods)} foods from PDF\n")

        if dry_run:
            # Show current DB counts so the user can see the before/after
            total_active = EthiopianFood.objects.filter(is_active=True).count()
            ephi_active  = EthiopianFood.objects.filter(is_active=True, source="ephi").count()
            other_active = total_active - ephi_active
            self.stdout.write(
                f"DB now: {total_active} active total "
                f"({ephi_active} EPHI + {other_active} other sources)\n"
            )
            for f in foods[:25]:
                self.stdout.write(
                    f"[{f['category']:10}] "
                    f"{f['display_name'][:70]:70} "
                    f"kcal={f['calories_kcal']:5.0f} "
                    f"iron={f['iron_mg']:4.1f} "
                    f"fiber={f['fiber_g']:4.1f} "
                    f"planner={'✓' if f['planner_weekly_safe'] else '⚠ limited'}"
                )
            return

        created = updated = skipped = errors = 0

        for food in foods:
            try:
                obj = EthiopianFood.objects.filter(slug=food["slug"]).first()

                if obj:
                    if update:
                        for k, v in food.items():
                            setattr(obj, k, v)
                        obj.save()
                        updated += 1
                    else:
                        skipped += 1
                else:
                    EthiopianFood.objects.create(**food)
                    created += 1

            except Exception as e:
                self.stdout.write(f"  ✗ Error {food['slug']}: {e}")
                errors += 1

        # Final count so the user can verify
        total_active = EthiopianFood.objects.filter(is_active=True).count()
        self.stdout.write(self.style.SUCCESS(
            f"\nDone → created:{created}  updated:{updated}  "
            f"skipped:{skipped}  errors:{errors}\n"
            f"Active foods in DB: {total_active}"
        ))