"""
community/models.py — Wellness Circles, Jebena, Gursha, Edir Fund, Feed

Self-contained models (no dependency on core.base.TimeStampedModel)
to eliminate any cross-app import issues during migration.
"""
import uuid
import random
import string
from django.db import models
from django.conf import settings
from django.utils import timezone


def generate_invite_code() -> str:
    """8-char uppercase alphanumeric code, e.g. JEBENA42"""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def default_expiry():
    return timezone.now() + timezone.timedelta(hours=24)


class WellnessCircle(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=100)
    name_am     = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True, default="")
    emoji       = models.CharField(max_length=10, default="🌿")
    invite_code = models.CharField(max_length=8, unique=True, default=generate_invite_code)

    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="circles_created",
    )

    group_gut_score     = models.IntegerField(default=0)
    group_streak_days   = models.IntegerField(default=0)
    total_meals_logged  = models.IntegerField(default=0)

    edir_balance_etb = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    edir_goal_etb    = models.DecimalField(max_digits=8, decimal_places=2, default=800)
    edir_target_pkg  = models.CharField(max_length=100, default="Kuriftu Group Wellness Package")

    is_public   = models.BooleanField(default=False)
    max_members = models.IntegerField(default=20)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.invite_code})"

    @property
    def member_count(self) -> int:
        return self.memberships.filter(is_active=True).count()

    @property
    def edir_progress_pct(self) -> int:
        if not self.edir_goal_etb:
            return 0
        pct = (float(self.edir_balance_etb) / float(self.edir_goal_etb)) * 100
        return min(int(pct), 100)


class CircleMembership(models.Model):
    ROLE_CHOICES = [("admin", "Admin"), ("member", "Member")]

    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(WellnessCircle, on_delete=models.CASCADE, related_name="memberships")
    user   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="circle_memberships",
    )
    role      = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    is_active = models.BooleanField(default=True)

    circle_gut_score = models.IntegerField(default=0)
    circle_streak    = models.IntegerField(default=0)
    gursha_given     = models.IntegerField(default=0)
    gursha_received  = models.IntegerField(default=0)
    edir_contributed = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("circle", "user")

    def __str__(self):
        return f"{self.user} in {self.circle}"


class JebenaCheckin(models.Model):
    """Daily coffee-ceremony wellness check-in for a circle."""
    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(WellnessCircle, on_delete=models.CASCADE, related_name="checkins")
    user   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="jebena_checkins",
    )
    date = models.DateField()

    food_slug    = models.CharField(max_length=60)
    food_name    = models.CharField(max_length=120)
    food_name_am = models.CharField(max_length=120, blank=True, default="")
    gut_score    = models.IntegerField(default=0)

    message    = models.CharField(max_length=200, blank=True, default="")
    mood_emoji = models.CharField(max_length=5, default="🌿")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("circle", "user", "date")
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.user} - {self.date} - {self.food_name}"


class GurshaChallenge(models.Model):
    """Recommend a food to a circle member — they log it, both earn points."""
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("expired", "Expired"),
        ("declined", "Declined"),
    ]

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gursha_sent",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gursha_received_set",
    )
    circle = models.ForeignKey(WellnessCircle, on_delete=models.CASCADE, related_name="gursha_challenges")

    food_slug    = models.CharField(max_length=60)
    food_name    = models.CharField(max_length=120)
    food_name_am = models.CharField(max_length=120, blank=True, default="")
    message      = models.CharField(max_length=200, blank=True, default="")

    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    expires_at = models.DateTimeField(default=default_expiry)

    points_from = models.IntegerField(default=0)
    points_to   = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.from_user} -> {self.to_user}: {self.food_name}"

    @property
    def is_expired(self) -> bool:
        return self.status == "pending" and timezone.now() > self.expires_at


class EdirContribution(models.Model):
    """Member contribution to a circle's shared wellness fund."""
    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(WellnessCircle, on_delete=models.CASCADE, related_name="edir_contributions")
    user   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="edir_contributions",
    )
    amount_etb   = models.DecimalField(max_digits=7, decimal_places=2)
    note         = models.CharField(max_length=100, blank=True, default="")
    is_confirmed = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} -> {self.circle}: {self.amount_etb} ETB"


class CommunityPost(models.Model):
    """Public wellness win shown on the community feed."""
    POST_TYPE_CHOICES = [
        ("streak", "Streak"),
        ("score", "Score"),
        ("gursha", "Gursha"),
        ("jebena", "Jebena"),
        ("kuriftu", "Kuriftu"),
        ("challenge", "Challenge"),
    ]

    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="community_posts",
    )
    circle = models.ForeignKey(
        WellnessCircle,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="circle_posts",
    )
    post_type = models.CharField(max_length=15, choices=POST_TYPE_CHOICES)
    title     = models.CharField(max_length=150)
    body      = models.CharField(max_length=300, blank=True, default="")
    emoji     = models.CharField(max_length=5, default="🌿")
    score     = models.IntegerField(default=0)
    streak    = models.IntegerField(default=0)

    is_anonymous = models.BooleanField(default=False)
    likes        = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}"
