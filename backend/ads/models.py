"""
ads/models.py — updated with payment tracking
Add these fields to your existing Advertisement model.
Run: python manage.py makemigrations ads && python manage.py migrate
"""
from django.db import models
from django.utils import timezone
from core.base import TimeStampedModel


class Advertisement(TimeStampedModel):

    CATEGORY_CHOICES = [
        ("spa",         "Spa & Wellness Centre"),
        ("gym",         "Gym & Fitness"),
        ("nutrition",   "Nutrition Clinic"),
        ("restaurant",  "Restaurant & Café"),
        ("food_product","Health Food Product"),
        ("pharmacy",    "Pharmacy & Supplements"),
        ("mental",      "Mental Health & Therapy"),
        ("retreat",     "Wellness Retreat"),
        ("other",       "Other Health Service"),
    ]

    PLACEMENT_CHOICES = [
        ("sidebar", "Desktop Sidebar"),
        ("banner",  "Mobile Banner"),
        ("both",    "Both"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("unpaid",    "Unpaid — awaiting payment"),
        ("paid",      "Paid — ready to activate"),
        ("overdue",   "Overdue — payment lapsed"),
        ("complimentary", "Complimentary — no charge"),
    ]

    TIER_CHOICES = [
        ("basic",    "Basic — 30 days, sidebar only"),
        ("standard", "Standard — 60 days, sidebar + banner"),
        ("premium",  "Premium — 90 days, all placements + priority"),
    ]

    TIER_PRICES_ETB = {
        "basic":    5_000,
        "standard": 12_000,
        "premium":  25_000,
    }

    # ── Advertiser info ───────────────────────────────────────────────────────
    business_name = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=30, blank=True)

    # ── Ad content ────────────────────────────────────────────────────────────
    title     = models.CharField(max_length=100)
    tagline   = models.CharField(max_length=160, blank=True)
    category  = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    placement = models.CharField(max_length=10, choices=PLACEMENT_CHOICES, default="both")
    image_url = models.URLField(blank=True)
    cta_label = models.CharField(max_length=50, default="Learn more")
    cta_url   = models.URLField()
    badge     = models.CharField(max_length=40, blank=True)

    # ── Payment ───────────────────────────────────────────────────────────────
    # Payment is handled offline (bank transfer / CBE Birr / in-person).
    # Admin marks payment_status manually after confirming receipt.
    # is_active must also be checked by admin — payment alone doesn't go live.
    tier           = models.CharField(
        max_length=20, choices=TIER_CHOICES, default="basic",
        help_text="Determines price, duration, and placement options"
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="unpaid"
    )
    amount_etb     = models.PositiveIntegerField(
        default=0,
        help_text="Amount agreed in ETB. Auto-filled from tier but can be overridden."
    )
    payment_reference = models.CharField(
        max_length=100, blank=True,
        help_text="Bank transfer ref, CBE Birr transaction ID, or receipt number"
    )
    payment_date = models.DateField(
        null=True, blank=True,
        help_text="Date payment was confirmed received"
    )
    invoice_note = models.TextField(
        blank=True,
        help_text="Internal notes about billing, discounts, or payment arrangement"
    )

    # ── Scheduling ────────────────────────────────────────────────────────────
    is_active = models.BooleanField(
        default=False,
        help_text="Admin must manually activate after confirming payment"
    )
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at   = models.DateTimeField(
        null=True, blank=True,
        help_text="Auto-set from tier duration on save if left blank"
    )

    # ── Targeting ─────────────────────────────────────────────────────────────
    priority        = models.IntegerField(default=0,
        help_text="Higher = shown first. Premium=30, Standard=20, Basic=10")
    target_fasting  = models.BooleanField(default=False)
    target_pregnant = models.BooleanField(default=False)
    target_diabetes = models.BooleanField(default=False)

    # ── Analytics ─────────────────────────────────────────────────────────────
    impressions = models.PositiveIntegerField(default=0)
    clicks      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-priority", "-starts_at"]

    def __str__(self):
        return f"{self.business_name} — {self.title} [{self.payment_status}]"

    def save(self, *args, **kwargs):
        # Auto-set amount from tier if not manually overridden
        if not self.amount_etb and self.tier in self.TIER_PRICES_ETB:
            self.amount_etb = self.TIER_PRICES_ETB[self.tier]
        # Auto-set priority from tier if still at default 0
        if self.priority == 0:
            self.priority = {"basic": 10, "standard": 20, "premium": 30}.get(self.tier, 0)
        # Auto-set ends_at from tier duration if not set
        if not self.ends_at and self.starts_at:
            days = {"basic": 30, "standard": 60, "premium": 90}.get(self.tier, 30)
            from datetime import timedelta
            self.ends_at = self.starts_at + timedelta(days=days)
        super().save(*args, **kwargs)

    @property
    def is_live(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.payment_status not in ("paid", "complimentary"):
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    @property
    def ctr(self) -> float:
        if not self.impressions:
            return 0.0
        return round((self.clicks / self.impressions) * 100, 2)