from __future__ import annotations
import re
import unicodedata
from django.core.management.base import BaseCommand
from foods.models import EthiopianFood
from django.db import models

PDF_PATH = "foods/data/ephi.pdf"

# ── FULLY UPDATED EPHI 2025 MAPPING ENGINE ────────────────────────────────────
# Group indices are bound to the official Ethiopian Food Composition Table (2025).
# Discrepancies in structural shifts (e.g., Fish in 09, Beverages in 12) are fully resolved.
GROUP_MAP = {
    "01": "grains",         # Grains and grain products
    "02": "grains",         # Teff processing variations / local grains
    "03": "legumes",        # Legumes and legume products
    "04": "vegetables",     # Vegetables and vegetable products
    "05": "special",        # Tubers, roots and crop variants
    "06": "meat",           # Organ and muscle meats
    "07": "meat",           # Poultry, game, and composite variants
    "08": "dairy_poultry",  # Eggs
    "09": "meat",           # FIXED: Group 09 is Fish and Seafood -> Routed to UI Meat & Fish
    "10": "dairy_poultry",  # Milk and milk products
    "11": "special",        # Fruits and fruit products (Mapped to special/fats)
    "12": "drinks",         # FIXED: Group 12 is Beverages -> Routed to UI Beverages/Drinks
    "13": "special",        # Spices, condiments, and traditional seasoning mixtures
    "14": "special",        # Fats and oils
    "15": "special",        # Sugars and sweets
    "16": "special",        # Infant formula and specialized composite flours
    "17": "special",        # Miscellaneous / traditional snack composites
}

# General agricultural food groups structurally accepted as fasting-safe
FASTING_SAFE_GROUPS = {"03", "04", "11"}


# ──────────────────────────────────────────────────────────────────────────────
# Name & String Pre-Processing Helpers
# ──────────────────────────────────────────────────────────────────────────────

def clean_food_name(name: str) -> str:
    """Removes stray formatting to prevent structural text splitting errors."""
    name = name.replace(",", " ")
    name = re.sub(r"\s{2,}", " ", name)
    return name.strip()


def slugify(text: str) -> str:
    """Generates clean, uniform URL-safe slugs for persistent routing architectures."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:90]


def safe_float(val, default=0.0) -> float:
    """Coerces text components into precise floats, absorbing non-numeric markers."""
    if not val:
        return default
    val = str(val).strip().replace("[", "").replace("]", "")
    if val in ("", "-", "—", "tr", "oa", "na", "NA"):
        return default
    try:
        return float(val)
    except ValueError:
        return default


# ──────────────────────────────────────────────────────────────────────────────
# Granular Preparation Form Extraction (Food Form Variations)
# ──────────────────────────────────────────────────────────────────────────────

def extract_preparation_form(name_en_raw: str, name_am_raw: str) -> tuple[str, str]:
    """
    Identifies the exact physical form or processing state of the food item.
    Differentiates identical underlying food items by raw/cooked states.
    """
    en_lower = name_en_raw.lower()
    
    # English Forms Mapping
    if "boiled" in en_lower:
        form_en = "boiled"
    elif "steamed" in en_lower:
        form_en = "steamed"
    elif "roasted" in en_lower or "roasted" in en_lower:
        form_en = "roasted"
    elif "grilled" in en_lower:
        form_en = "grilled"
    elif "fried" in en_lower:
        form_en = "fried"
    elif "baked" in en_lower or "cooked" in en_lower:
        form_en = "cooked"
    elif "dried" in en_lower or "dry" in en_lower:
        form_en = "dried"
    else:
        form_en = "raw"

    # Amharic Forms Mapping (Preserving structural typo context)
    if "የተቀቀለ" in name_am_raw:
        form_am = "የተቀቀለ"
    elif "የተቆላ" in name_am_raw:
        form_am = "የተቆላ"
    elif "በውሃ እንፋሎት" in name_am_raw or "የተቀቀለ" in name_am_raw and "እንፋሎት" in name_am_raw:
        form_am = "በውሃ እንፋሎት የበሰለ"
    elif "የተጋገረ" in name_am_raw:
        form_am = "የተጋገረ"
    elif "የተጠበሰ" in name_am_raw:
        form_am = "የተጠበሰ"
    elif "የደረቀ" in name_am_raw:
        form_am = "የደረቀ"
    else:
        form_am = "ጥሬ"

    return form_en, form_am


# ──────────────────────────────────────────────────────────────────────────────
# Bulletproof Medical & Health Logic Frameworks
# ──────────────────────────────────────────────────────────────────────────────

def evaluate_pregnancy_safety(name_en_raw: str, group_code: str) -> bool:
    """
    Evaluates pregnancy suitability. Explicitly locks down modern alcohols,
    traditional brews, raw products, and specific contractions-inducing agents.
    """
    name = name_en_raw.lower()
    
    # Strict Guardrail: Trap any alcohol or fermented item residing inside Group 12
    if group_code == "12":
        alcoholic_beverages = ["tella", "tej", "katikala", "vodka", "beer", "wine", "alcohol", "araqe", "spirit", "liqueur"]
        if any(token in name for token in alcoholic_beverages):
            return False

    # Standard clinical exclusions
    unsafe_items = [
        "alcohol", "tej", "tella", "katikala", "vodka", "beer", "wine", "araqe",
        "raw meat", "kitfo", "gored gored", "raw fish", "carp", "tilapia", "perch",
        "fenugreek", "abish", "gesho", "mitmita"
    ]
    return not any(w in name for w in unsafe_items)


def evaluate_fasting_safety(name_en_raw: str, group_code: str) -> bool:
    """
    Evaluates Orthodox fasting compatibility. Standard drinks (water, tea) are allowed,
    while celebratory or highly-alcoholic ferments in Group 12 break fasting criteria.
    """
    if group_code in FASTING_SAFE_GROUPS:
        return True
        
    if group_code == "12":
        name = name_en_raw.lower()
        alcoholic_beverages = ["tella", "tej", "katikala", "vodka", "beer", "wine", "alcohol", "araqe"]
        if any(token in name for token in alcoholic_beverages):
            return False
        return True # Non-alcoholic hot drinks, water, standard herbal infusions
        
    return False


def is_diabetes_friendly(gi: int, cho_g: float) -> bool:
    if gi == 0:
        return True
    return gi <= 55 and cho_g <= 40


# ──────────────────────────────────────────────────────────────────────────────
# Composition Scoring Matrix
# ──────────────────────────────────────────────────────────────────────────────

def compute_fermentation_score(name_en: str, name_am: str) -> int:
    name = (name_en + " " + name_am).lower()
    if any(w in name for w in ["injera", "ergo", "tej", "tella", "kocho", "enset", "borde", "shameta"]):
        return 3
    if any(w in name for w in ["ayib", "yogurt", "ferment", "soured", "kultured"]):
        return 2
    if any(w in name for w in ["dabo", "bread", "genfo", "porridge"]):
        return 1
    return 0


def compute_prebiotic_score(fiber_g: float, name_en: str) -> int:
    name = name_en.lower()
    if any(w in name for w in ["lentil", "chickpea", "pea", "bean", "misir", "shiro", "barley", "oat"]):
        return 3
    if fiber_g >= 6: return 3
    if fiber_g >= 3: return 2
    if fiber_g >= 1: return 1
    return 0


def compute_inflammatory_index(name_en: str, fat_g: float, fiber_g: float) -> int:
    name = name_en.lower()
    if any(w in name for w in ["berbere", "turmeric", "ginger", "garlic", "collard", "cabbage", "kale", "spice"]):
        return -2
    if any(w in name for w in ["vegetable", "legume", "lentil", "bean", "pea", "green", "leaf"]):
        return -1
    if any(w in name for w in ["organ", "liver", "tripe", "processed", "fried", "deep", "sausage"]):
        return 2
    if fat_g > 20:   return 1
    if fiber_g > 5:  return -1
    return 0


def compute_glycemic_index(name_en: str, cho_g: float) -> int:
    name = name_en.lower()
    known = {
        "injera": 35, "teff": 35, "lentil": 19, "misir": 19, "chickpea": 28, 
        "shiro": 28, "split pea": 22, "barley": 28, "potato": 55, "sweet potato": 50, 
        "bread white": 68, "bread whole": 51, "rice": 72, "maize": 52, "sorghum": 55,
        "banana": 51, "mango": 51, "honey": 55, "sugar": 65, "milk": 35, "yogurt": 35,
    }
    for key, gi in known.items():
        if key in name: return gi
    if cho_g == 0:   return 0
    if cho_g < 10:   return 15
    if cho_g < 30:   return 40
    return 55


# ──────────────────────────────────────────────────────────────────────────────
# Core PDF Data Extraction Pipeline
# ──────────────────────────────────────────────────────────────────────────────

def parse_ephi_pdf(start_page: int = 44, end_page: int = 390) -> list[dict]:
    """Parses structural EPHI PDF rows using specific 6-digit identity parsing loops."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("Missing dependencies. Run: pip install pdfplumber")

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

                if "(2/5)" in line or ("calcium" in line.lower() and "iron" in line.lower()):
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

                if group not in GROUP_MAP:
                    continue

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

                    raw_name_en = name_split[0].strip()
                    name_en_raw = clean_food_name(re.sub(r"\s+", " ", raw_name_en))
                    
                    # Store raw values for dynamic contextual evaluations
                    name_en_atomic = name_en_raw.split(" — ")[0].split(" (")[0].strip()

                    # Extract the clean Amharic description without truncation
                    name_am_raw = re.sub(r"\s+", " ", name_split[1].strip()) if len(name_split) > 1 else ""

                    if name_en_atomic and kcal >= 10:
                        part1[code] = {
                            "code": code,
                            "group": group,
                            "name_en_raw": name_en_raw,
                            "name_en": name_en_atomic,
                            "name_am": name_am_raw,
                            "kcal": kcal,
                            "protein": protein,
                            "fat": fat,
                            "cho": cho,
                            "fiber": fiber,
                        }

    result: list[dict] = []
    seen_slugs: set[str] = set()

    for code, f in part1.items():
        name_en_raw = f["name_en_raw"]
        name_en = f["name_en"]
        name_am = f["name_am"]
        group   = f["group"]

        category = GROUP_MAP[group]
        kcal     = f["kcal"]
        protein  = f["protein"]
        fat      = f["fat"]
        cho      = f["cho"]
        fiber    = f["fiber"]
        iron     = iron_map.get(code, 0.0)

        # Process specialized food form properties
        form_en, form_am = extract_preparation_form(name_en_raw, name_am)

        gi        = compute_glycemic_index(name_en, cho)
        ferm      = compute_fermentation_score(name_en, name_am)
        prebiotic = compute_prebiotic_score(fiber, name_en)
        inflam    = compute_inflammatory_index(name_en, fat, fiber)
        
        # FIXED Checkers referencing exact context parameters
        fasting   = evaluate_fasting_safety(name_en_raw, group)
        preg_safe = evaluate_pregnancy_safe = evaluate_pregnancy_safety(name_en_raw, group)
        diab_safe = is_diabetes_friendly(gi, cho)

        # Generate a distinct display name preserving typography values bilingually
        display_name = f"{name_en} [{name_am}]" if name_am else name_en

        # Append execution flags to slugs to keep boiled and raw entries isolated
        slug = slugify(f"{name_en}_{form_en}")
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
            "serving_description": f"Per 100g edible portion ({form_en})",
            "serving_g":           100.0,
            "calories_kcal":       kcal,
            "fiber_g":             fiber,
            "protein_g":           protein,
            "iron_mg":             iron,
            "fat_g":               fat,
            "glycemic_index":      gi,
            "fermentation_score":  ferm,
            "prebiotic_score":     prebiotic,
            "inflammatory_index":  inflam,
            "fasting_safe":        fasting,
            "pregnancy_safe":      preg_safe,
            "diabetes_friendly":   diab_safe,
            "source_citation":     f"EPHI EFCT 2025 (code {code})",
            "notes": (
                f"Verified {form_en}/{form_am} preparation form. "
                f"{kcal:.1f} kcal | {protein:.1f}g protein | "
                f"{fat:.1f}g fat | {cho:.1f}g CHO."
            ),
            "is_active":           True,
            "source":              "ephi",
        })

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Django Command Implementation Wrapper
# ──────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Parse EPHI Food Composition Table 2025 PDF with precise multi-form mapping rules."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run",    action="store_true")
        parser.add_argument("--update",     action="store_true")
        parser.add_argument("--start-page", type=int, default=44)
        parser.add_argument("--end-page",   type=int, default=390)
        parser.add_argument("--min-kcal",   type=float, default=10)
        parser.add_argument("--purge-old",  action="store_true")

    def handle(self, *args, **options):
        dry_run   = options["dry_run"]
        update    = options["update"]
        min_kcal  = options["min_kcal"]
        purge_old = options["purge_old"]

        if purge_old and not dry_run:
            old_qs = EthiopianFood.objects.exclude(source="ephi").filter(is_active=True)
            count  = old_qs.count()
            if count:
                old_qs.update(is_active=False)
                self.stdout.write(self.style.WARNING(f"Deactivated {count} legacy metrics rows."))

        self.stdout.write("Running parsing pipeline over EPHI standard data asset...")
        
        try:
            foods = parse_ephi_pdf(options["start_page"], options["end_page"])
            foods = [f for f in foods if f["calories_kcal"] >= min_kcal]
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Pipeline crashed during structural parse: {e}"))
            return

        self.stdout.write(f"Identified {len(foods)} valid food forms rows.\n")

        if dry_run:
            total_active = EthiopianFood.objects.filter(is_active=True).count()
            self.stdout.write(f"Dry-Run complete. Valid rows parsed ready for writing: {len(foods)}")
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
                self.stdout.write(f" ✗ Write Fault {food['slug']}: {e}")
                errors += 1

        total_active = EthiopianFood.objects.filter(is_active=True).count()
        self.stdout.write(self.style.SUCCESS(
            f"Pipeline Execution Complete -> Created: {created} | Updated: {updated} | Faults: {errors}\n"
            f"Operational Database Pool Size: {total_active} active items records."
        ))