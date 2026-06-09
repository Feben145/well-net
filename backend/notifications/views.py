"""notifications/views.py"""
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import serializers

from .models import OffPeakDeal, Notification
from core.base import IsKuriftuPartner


# ── Serializers ───────────────────────────────────────────────────────────────

class OffPeakDealSerializer(serializers.ModelSerializer):
    slots_remaining = serializers.ReadOnlyField()
    class Meta:
        model = OffPeakDeal
        fields = [
            "id", "title", "deal_type", "description", "location",
            "original_price_etb", "discounted_price_etb", "discount_pct",
            "valid_from", "valid_until", "slots_remaining", "booking_url",
        ]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "notif_type", "title", "body", "sent_at", "opened", "channel"]


# ── Views ─────────────────────────────────────────────────────────────────────

class ActiveDealsView(generics.ListAPIView):
    """
    GET /api/v1/notifications/deals/
    Returns active Kuriftu off-peak deals matching user's gut score.
    """
    serializer_class = OffPeakDealSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        now = timezone.now()
        profile = getattr(self.request.user, "profile", None)
        score = getattr(profile, "current_gut_score", 50) if profile else 50

        return OffPeakDeal.objects.filter(
            is_active=True,
            valid_until__gte=now,
            min_gut_score__lte=score,
            max_gut_score__gte=score,
        )


class NotificationHistoryView(generics.ListAPIView):
    """GET /api/v1/notifications/history/"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-sent_at")[:50]


@api_view(["POST"])
@permission_classes([IsKuriftuPartner])
def create_deal(request):
    """
    POST /api/v1/notifications/deals/create/
    Kuriftu partner API — creates a new off-peak deal.
    Authenticated via X-Kuriftu-Key header.
    """
    serializer = OffPeakDealSerializer(data=request.data)
    if serializer.is_valid():
        deal = serializer.save()
        # Trigger async notifications immediately
        from .tasks import send_offpeak_deals
        send_offpeak_deals.delay()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
