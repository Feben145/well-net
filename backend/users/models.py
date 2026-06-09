"""
users/models.py
Custom User + UserProfile — the wellness identity layer.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.base import TimeStampedModel


class User(AbstractUser):
    """
    Extended Django user.
    Keep auth fields on AbstractUser; wellness profile goes on UserProfile.
    """
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(
        max_length=10,
        choices=[("en", "English"), ("am", "Amharic")],
        default="en",
    )
    sms_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class UserProfile(TimeStampedModel):
    """
    Wellness identity — one-to-one with User.
    Drives all personalisation in the scoring engine and AI.
    """

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
        ("prefer_not", "Prefer not to say"),
    ]

    ACTIVITY_CHOICES = [
        ("sedentary", "Sedentary (desk job, little exercise)"),
        ("light", "Light (1–2 days exercise/week)"),
        ("moderate", "Moderate (3–4 days/week)"),
        ("active", "Active (5+ days/week)"),
    ]

    WELLNESS_GOAL_CHOICES = [
        ("gut_health", "Improve gut health"),
        ("weight_balance", "Weight balance"),
        ("energy", "Boost energy"),
        ("stress", "Reduce stress"),
        ("sleep", "Better sleep"),
        ("immunity", "Build immunity"),
        ("mindfulness", "Mindful living"),
        ("general", "General wellness"),
    ]

    DIET_TYPE_CHOICES = [
        ("omnivore", "Omnivore"),
        ("fasting", "Ethiopian Orthodox fasting"),
        ("vegetarian", "Vegetarian"),
        ("vegan", "Vegan"),
        ("no_pork", "No pork"),
        ("diabetic", "Diabetic-friendly"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)

    # Wellness identity
    primary_goal = models.CharField(
        max_length=30, choices=WELLNESS_GOAL_CHOICES, default="general"
    )
    secondary_goals = models.JSONField(default=list)   # list of goal keys
    activity_level = models.CharField(
        max_length=20, choices=ACTIVITY_CHOICES, default="moderate"
    )
    diet_type = models.CharField(
        max_length=20, choices=DIET_TYPE_CHOICES, default="omnivore"
    )

    # Medical flags (drive scoring overrides)
    is_pregnant = models.BooleanField(default=False)
    has_diabetes = models.BooleanField(default=False)
    has_hypertension = models.BooleanField(default=False)
    has_anemia = models.BooleanField(default=False)

    # Fasting mode
    is_fasting_season = models.BooleanField(default=False)

    # Kuriftu affiliation
    kuriftu_guest = models.BooleanField(default=False)
    kuriftu_membership_tier = models.CharField(
        max_length=20,
        choices=[("none","None"),("standard","Standard"),("premium","Premium")],
        default="none",
    )

    # Computed — updated by scoring engine after each meal log
    current_gut_score = models.IntegerField(default=0)
    current_wellness_score = models.IntegerField(default=0)
    wellness_streak_days = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.email} — {self.primary_goal}"

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg:
            h = self.height_cm / 100
            return round(self.weight_kg / (h * h), 1)
        return None


class FamilyMember(TimeStampedModel):
    """
    Family planner — additional profiles linked to one account.
    Supports child, elder, pregnancy sub-profiles.
    """
    MEMBER_TYPE_CHOICES = [
        ("adult", "Adult"),
        ("child", "Child"),
        ("elder", "Elder"),
        ("pregnant", "Pregnant"),
        ("infant", "Infant"),
    ]

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="family_members"
    )
    name = models.CharField(max_length=100)
    member_type = models.CharField(max_length=20, choices=MEMBER_TYPE_CHOICES)
    age_years = models.IntegerField(null=True, blank=True)
    diet_type = models.CharField(max_length=20, blank=True)
    has_diabetes = models.BooleanField(default=False)
    has_anemia = models.BooleanField(default=False)
    current_gut_score = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.member_type}) — {self.owner.email}"
