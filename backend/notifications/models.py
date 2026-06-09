"""
notifications/models.py + tasks.py
Off-peak Kuriftu deals, daily wellness SMS, weekly reports.
"""
from django.db import models
from django.contrib.auth import get_user_model
from core.base import TimeStampedModel

User = get_user_model()


class OffPeakDeal(TimeStampedModel):
    """
    Kuriftu off-peak wellness slot — pushed to matching users via SMS/push.
    Created via Kuriftu partner API or admin.
    """
    DEAL_TYPE_CHOICES = [
        ("spa",       "Spa treatment"),
        ("retreat",   "Wellness retreat"),
        ("yoga",      "Yoga / movement session"),
        ("dining",    "Wellness dining"),
        ("group",     "Group package"),
        ("consult",   "Nutritionist consult"),
    ]

    title = models.CharField(max_length=200)
    deal_type = models.CharField(max_length=20, choices=DEAL_TYPE_CHOICES)
    description = models.TextField()
    location = models.CharField(max_length=100, help_text="e.g. Kuriftu Bishoftu")
    original_price_etb = models.DecimalField(max_digits=8, decimal_places=2)
    discounted_price_etb = models.DecimalField(max_digits=8, decimal_places=2)
    discount_pct = models.IntegerField()

    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    slots_available = models.IntegerField(default=10)
    slots_booked = models.IntegerField(default=0)

    # Targeting: match by gut score range and/or Kuriftu tier
    min_gut_score = models.IntegerField(default=0)
    max_gut_score = models.IntegerField(default=100)
    kuriftu_tier_required = models.CharField(max_length=20, default="none")

    is_active = models.BooleanField(default=True)
    booking_url = models.URLField(blank=True)

    class Meta:
        ordering = ["valid_from"]

    def __str__(self):
        return f"{self.title} — {self.discounted_price_etb} ETB"

    @property
    def slots_remaining(self):
        return self.slots_available - self.slots_booked


class Notification(TimeStampedModel):
    """Log of all notifications sent to users."""
    CHANNEL_CHOICES = [
        ("sms", "SMS"), ("push", "Push"), ("email", "Email"),
        ("telegram", "Telegram"), ("whatsapp", "WhatsApp"),
    ]
    TYPE_CHOICES = [
        ("daily_tip", "Daily wellness tip"),
        ("weekly_report", "Weekly report"),
        ("off_peak_deal", "Off-peak deal"),
        ("score_milestone", "Score milestone"),
        ("streak", "Streak alert"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    notif_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    opened = models.BooleanField(default=False)
    deal = models.ForeignKey(OffPeakDeal, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} — {self.notif_type} via {self.channel}"
