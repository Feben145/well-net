"""
community/models.py — Wellness Circles, Jebena, Gursha, Edir Fund, Feed
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from core.base import TimeStampedModel

User = get_user_model()


class WellnessCircle(TimeStampedModel):
    """Private wellness group — like an eder but for gut health."""
    name        = models.CharField(max_length=100)
    name_am     = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    emoji       = models.CharField(max_length=10, default="🌿")
    invite_code = models.CharField(max_length=8, unique=True)
    created_by  = models.ForeignKey(User, on_delete=models.CASCADE, related_name="circles_created")

    group_gut_score    = models.IntegerField(default=0)
    group_streak_days  = models.IntegerField(default=0)
    total_meals_logged = models.IntegerField(default=0)

    edir_balance_etb   = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    edir_goal_etb      = models.DecimalField(max_digits=8, decimal_places=2, default=800)
    edir_target_pkg    = models.CharField(max_length=100, default="Kuriftu Group Wellness Package")

    is_public   = models.BooleanField(default=False)
    max_members = models.IntegerField(default=20)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.member_count} members)"

    @property
    def member_count(self):
        return self.memberships.filter(is_active=True).count()

    @property
    def edir_progress_pct(self):
        if not self.edir_goal_etb:
            return 0
        return min(int((self.edir_balance_etb / self.edir_goal_etb) * 100), 100)


class CircleMembership(TimeStampedModel):
    ROLE_CHOICES = [("admin", "Admin"), ("member", "Member")]
    circle             = models.ForeignKey(WellnessCircle, on_delete=models.CASCADE, related_name="memberships")
    user               = models.ForeignKey(User, on_delete=models.CASCADE, related_name="circle_memberships")
    role               = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    is_active          = models.BooleanField(default=True)
    circle_gut_score   = models.IntegerField(default=0)
    circle_streak      = models.IntegerField(default=0)
    gursha_given       = models.IntegerField(default=0)
    gursha_received    = models.IntegerField(default=0)
    edir_contributed   = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        unique_together = ("circle", "user")


class JebenaCheckin(TimeStampedModel):
    """Daily coffee-ceremony wellness check-in for a circle."""
    circle       = models.ForeignKey(WellnessCircle, on_delete=models.CASCADE, related_name="checkins")
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="jebena_checkins")
    date         = models.DateField()
    food_slug    = models.CharField(max_length=60)
    food_name    = models.CharField(max_length=120)
    food_name_am = models.CharField(max_length=120, blank=True)
    gut_score    = models.IntegerField(default=0)
    message      = models.CharField(max_length=200, blank=True)
    mood_emoji   = models.CharField(max_length=5, default="🌿")

    class Meta:
        unique_together = ("circle", "user", "date")
        ordering = ["-date", "-created_at"]


class GurshaChallenge(TimeStampedModel):
    """Recommend a food to a circle member — they log it, both earn points."""
    STATUS_CHOICES = [
        ("pending", "Pending"), ("accepted", "Accepted"),
        ("expired", "Expired"), ("declined", "Declined"),
    ]
    from_user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name="gursha_sent")
    to_user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name="gursha_received_set")
    circle       = models.ForeignKey(WellnessCircle, on_delete=models.CASCADE, related_name="gursha_challenges")
    food_slug    = models.CharField(max_length=60)
    food_name    = models.CharField(max_length=120)
    food_name_am = models.CharField(max_length=120, blank=True)
    message      = models.CharField(max_length=200, blank=True)
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    expires_at   = models.DateTimeField()
    points_from  = models.IntegerField(default=0)
    points_to    = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.status == "pending" and timezone.now() > self.expires_at


class EdirContribution(TimeStampedModel):
    """Member contribution to the circle's shared wellness fund."""
    circle       = models.ForeignKey(WellnessCircle, on_delete=models.CASCADE, related_name="edir_contributions")
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="edir_contributions")
    amount_etb   = models.DecimalField(max_digits=7, decimal_places=2)
    note         = models.CharField(max_length=100, blank=True)
    is_confirmed = models.BooleanField(default=True)


class CommunityPost(TimeStampedModel):
    """Public wellness win on the community feed."""
    POST_TYPE_CHOICES = [
        ("streak", "Streak"), ("score", "Score"), ("gursha", "Gursha"),
        ("jebena", "Jebena"), ("kuriftu", "Kuriftu"), ("challenge", "Challenge"),
    ]
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="community_posts")
    circle       = models.ForeignKey(WellnessCircle, on_delete=models.SET_NULL, null=True, blank=True, related_name="circle_posts")
    post_type    = models.CharField(max_length=15, choices=POST_TYPE_CHOICES)
    title        = models.CharField(max_length=150)
    body         = models.CharField(max_length=300, blank=True)
    emoji        = models.CharField(max_length=5, default="🌿")
    score        = models.IntegerField(default=0)
    streak       = models.IntegerField(default=0)
    is_anonymous = models.BooleanField(default=False)
    likes        = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]