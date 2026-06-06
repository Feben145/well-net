"""experts/views.py"""
from rest_framework import generics, permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import ProfessionalProfile, ExpertSession
from core.base import IsVerifiedProfessional


# ── Serializers ───────────────────────────────────────────────────────────────

class ProfessionalListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalProfile
        fields = [
            "id", "display_name", "title", "specialty", "bio",
            "languages", "session_types", "session_price_etb",
            "offpeak_price_etb", "rating", "review_count",
            "is_verified", "is_kuriftu_partner", "avatar_url",
            "license_body",
        ]


class SessionBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpertSession
        fields = ["professional", "scheduled_at", "duration_minutes", "session_type"]


class SessionSerializer(serializers.ModelSerializer):
    professional = ProfessionalListSerializer(read_only=True)
    class Meta:
        model = ExpertSession
        fields = "__all__"
        read_only_fields = ["client", "price_paid_etb", "platform_fee_etb", "status"]


# ── Views ─────────────────────────────────────────────────────────────────────

class ProfessionalListView(generics.ListAPIView):
    """
    GET /api/v1/experts/?specialty=dietitian&is_kuriftu_partner=true
    Public listing of verified professionals.
    """
    serializer_class = ProfessionalListSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ["specialty", "is_kuriftu_partner", "is_verified"]

    def get_queryset(self):
        return ProfessionalProfile.objects.filter(is_verified=True)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def book_session(request, professional_id):
    """
    POST /api/v1/experts/<id>/book/
    Books a session and calculates platform fee.
    """
    try:
        pro = ProfessionalProfile.objects.get(id=professional_id, is_verified=True)
    except ProfessionalProfile.DoesNotExist:
        return Response({"error": "Professional not found."}, status=404)

    serializer = SessionBookSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    session = ExpertSession.objects.create(
        professional=pro,
        client=request.user,
        price_paid_etb=pro.session_price_etb,
        platform_fee_etb=pro.platform_fee,
        **serializer.validated_data,
    )
    return Response(SessionSerializer(session).data, status=201)


class MySessionsView(generics.ListAPIView):
    """GET /api/v1/experts/my-sessions/"""
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExpertSession.objects.filter(client=self.request.user)
