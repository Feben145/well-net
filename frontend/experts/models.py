"""experts/models.py — Licensed health professional marketplace"""
from django.db import models
from django.contrib.auth import get_user_model
from core.base import TimeStampedModel

User = get_user_model()


class ProfessionalProfile(TimeStampedModel):
    SPECIALTY_CHOICES = [
        ("dietitian",       "Registered Dietitian"),
        ("nutritionist",    "Certified Nutritionist"),
        ("gastroenterologist", "Gastroenterologist"),
        ("general_physician",  "General Physician"),
        ("wellness_coach",  "Wellness Coach"),
        ("yoga_instructor", "Yoga Instructor"),     # Kuriftu yoga partners
        ("fitness_trainer", "Fitness Trainer"),
    ]
    LICENSE_BODY_CHOICES = [
        ("moh",     "Ministry of Health Ethiopia"),
        ("fmhaca",  "FMHACA"),
        ("kuriftu", "Kuriftu Wellness Partner"),
        ("other",   "Other"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="professional_profile"
    )
    display_name = models.CharField(max_length=100)
    title = models.CharField(max_length=50, help_text="e.g. Dr., RD, CNS")
    specialty = models.CharField(max_length=30, choices=SPECIALTY_CHOICES)
    bio = models.TextField(max_length=500)
    languages = models.JSONField(default=list)       # ["Amharic", "English"]
    session_types = models.JSONField(default=list)   # ["video", "in-person", "group"]

    # License verification
    license_number = models.CharField(max_length=100)
    license_body = models.CharField(max_length=20, choices=LICENSE_BODY_CHOICES)
    is_verified = models.BooleanField(default=False)
    is_kuriftu_partner = models.BooleanField(default=False)

    # Pricing
    session_price_etb = models.DecimalField(max_digits=7, decimal_places=2)
    offpeak_price_etb = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
        help_text="Discounted price for off-peak slots"
    )

    # Platform commission: 20%
    PLATFORM_COMMISSION = 0.20

    rating = models.FloatField(default=0.0)
    review_count = models.IntegerField(default=0)
    total_sessions = models.IntegerField(default=0)
    avatar_url = models.URLField(blank=True)

    class Meta:
        ordering = ["-is_verified", "-rating"]

    def __str__(self):
        return f"{self.title} {self.display_name} — {self.specialty}"

    @property
    def platform_fee(self):
        return round(float(self.session_price_etb) * self.PLATFORM_COMMISSION, 2)


class ExpertSession(TimeStampedModel):
    """Booked session between user and professional."""
    STATUS_CHOICES = [
        ("pending",   "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    professional = models.ForeignKey(
        ProfessionalProfile, on_delete=models.CASCADE, related_name="sessions"
    )
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="expert_sessions"
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    session_type = models.CharField(max_length=20)   # video | in-person | group
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    price_paid_etb = models.DecimalField(max_digits=7, decimal_places=2)
    platform_fee_etb = models.DecimalField(max_digits=7, decimal_places=2)

    # Post-session: professional records notes → updates client's WellNet profile
    session_notes = models.TextField(blank=True)
    recommendations = models.JSONField(default=list)

    class Meta:
        ordering = ["-scheduled_at"]
