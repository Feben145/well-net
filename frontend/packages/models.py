"""packages/models.py + views.py + urls.py — Wellness packages"""
# ── models.py ─────────────────────────────────────────────────────────────────
from django.db import models
from django.contrib.auth import get_user_model
from core.base import TimeStampedModel

User = get_user_model()


class WellnessPackage(TimeStampedModel):
    PACKAGE_TYPE_CHOICES = [
        ("individual", "Individual Premium"),
        ("family",     "Family Plan"),
        ("group",      "Group / Friends"),
        ("corporate",  "Corporate Wellness"),
        ("kuriftu",    "Kuriftu Resort Bundle"),
    ]

    name = models.CharField(max_length=100)
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPE_CHOICES)
    tagline = models.CharField(max_length=200)
    price_etb = models.DecimalField(max_digits=8, decimal_places=2)
    billing_period = models.CharField(
        max_length=20,
        choices=[("monthly","Monthly"),("annual","Annual"),("one_time","One-time")],
        default="monthly",
    )
    max_members = models.IntegerField(default=1)
    features = models.JSONField(default=list)   # list of feature strings
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    kuriftu_discount_pct = models.IntegerField(default=0)

    class Meta:
        ordering = ["price_etb"]

    def __str__(self):
        return f"{self.name} — {self.price_etb} ETB"


class UserSubscription(TimeStampedModel):
    STATUS_CHOICES = [
        ("active","Active"),("expired","Expired"),("cancelled","Cancelled"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    package = models.ForeignKey(WellnessPackage, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    members_count = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.user.email} — {self.package.name}"


# ── views.py ──────────────────────────────────────────────────────────────────
from rest_framework import generics, permissions, serializers


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WellnessPackage
        fields = [
            "id", "name", "package_type", "tagline", "price_etb",
            "billing_period", "max_members", "features",
            "is_featured", "kuriftu_discount_pct",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    package = PackageSerializer(read_only=True)
    class Meta:
        model = UserSubscription
        fields = ["id", "package", "status", "started_at", "expires_at", "members_count"]


class PackageListView(generics.ListAPIView):
    """GET /api/v1/packages/ — public"""
    serializer_class = PackageSerializer
    permission_classes = [permissions.AllowAny]
    queryset = WellnessPackage.objects.filter(is_active=True)


class MySubscriptionsView(generics.ListAPIView):
    """GET /api/v1/packages/my/"""
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user, status="active")
