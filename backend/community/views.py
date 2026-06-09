"""community/views.py"""
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models import F
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import (
    WellnessCircle, CircleMembership,
    JebenaCheckin, GurshaChallenge,
    EdirContribution, CommunityPost,
)
from .serializers import (
    WellnessCircleSerializer, JebenaCheckinSerializer,
    GurshaChallengeSerializer, EdirContributionSerializer,
    CommunityPostSerializer,
)

User = get_user_model()


# ── Circles ───────────────────────────────────────────────────────────────────

class MyCirclesView(generics.ListCreateAPIView):
    """GET/POST /api/v1/community/circles/"""
    serializer_class   = WellnessCircleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WellnessCircle.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
        ).distinct()

    def get_serializer_context(self):
        return {"request": self.request}


class CircleDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/community/circles/<id>/"""
    serializer_class   = WellnessCircleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WellnessCircle.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
        )

    def get_serializer_context(self):
        return {"request": self.request}


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def join_circle(request):
    """POST /api/v1/community/circles/join/  { invite_code: "ABC12345" }"""
    code = request.data.get("invite_code", "").upper().strip()
    if not code:
        return Response({"error": "invite_code is required."}, status=400)

    try:
        circle = WellnessCircle.objects.get(invite_code=code)
    except WellnessCircle.DoesNotExist:
        return Response({"error": "Invalid invite code — check and try again."}, status=404)

    if circle.member_count >= circle.max_members:
        return Response({"error": "This circle is full (max members reached)."}, status=400)

    membership, created = CircleMembership.objects.get_or_create(
        circle=circle, user=request.user,
        defaults={"role": "member", "is_active": True},
    )
    if not created and not membership.is_active:
        membership.is_active = True
        membership.save(update_fields=["is_active"])

    return Response(
        WellnessCircleSerializer(circle, context={"request": request}).data,
        status=201 if created else 200,
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def leave_circle(request, circle_id):
    """POST /api/v1/community/circles/<id>/leave/"""
    membership = CircleMembership.objects.filter(
        circle_id=circle_id, user=request.user, is_active=True
    ).first()
    if not membership:
        return Response({"error": "You are not a member of this circle."}, status=404)

    if membership.role == "admin":
        other = CircleMembership.objects.filter(
            circle_id=circle_id, role="admin", is_active=True
        ).exclude(user=request.user).exists()
        if not other:
            return Response(
                {"error": "Assign another admin before leaving."}, status=400
            )

    membership.is_active = False
    membership.save(update_fields=["is_active"])
    return Response({"ok": True})


# ── Jebena check-in ───────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def jebena_checkin(request):
    """
    POST /api/v1/community/jebena/
    { circle_id, food_slug, message?, mood_emoji? }
    """
    circle_id = request.data.get("circle_id")
    food_slug = request.data.get("food_slug", "").strip()
    message   = request.data.get("message", "").strip()
    mood      = request.data.get("mood_emoji", "🌿")

    if not circle_id or not food_slug:
        return Response({"error": "circle_id and food_slug are required."}, status=400)

    # Validate membership
    try:
        circle = WellnessCircle.objects.get(id=circle_id)
    except WellnessCircle.DoesNotExist:
        return Response({"error": "Circle not found."}, status=404)

    if not circle.memberships.filter(user=request.user, is_active=True).exists():
        return Response({"error": "You are not a member of this circle."}, status=403)

    # Get food from DB
    from foods.models import EthiopianFood
    from foods.scoring import compute_gut_score, FoodItem

    food = EthiopianFood.objects.filter(slug=food_slug).first()
    if not food:
        # Try partial match
        food = EthiopianFood.objects.filter(slug__icontains=food_slug).first()
    if not food:
        return Response({"error": f"Food '{food_slug}' not found in database."}, status=404)

    # Score this single food
    result = compute_gut_score([FoodItem(
        slug=food.slug,
        fiber_g=food.fiber_g,
        protein_g=food.protein_g,
        iron_mg=food.iron_mg,
        fermentation_score=food.fermentation_score,
        inflammatory_index=food.inflammatory_index,
        prebiotic_score=food.prebiotic_score,
    )])

    # Upsert today's check-in
    checkin, created = JebenaCheckin.objects.update_or_create(
        circle=circle, user=request.user, date=date.today(),
        defaults={
            "food_slug":    food.slug,
            "food_name":    food.name_en.split(" — ")[0].split(" (")[0],
            "food_name_am": food.name_am or "",
            "gut_score":    result.gut_score,
            "message":      message,
            "mood_emoji":   mood,
        },
    )

    # Update group average score
    _refresh_group_score(circle)

    # Update member's score
    CircleMembership.objects.filter(
        circle=circle, user=request.user
    ).update(circle_gut_score=result.gut_score)

    # Auto-post milestone to community feed if score is high
    if result.gut_score >= 80 and circle.is_public:
        _post_milestone(request.user, circle, result.gut_score)

    return Response({
        "checkin":     JebenaCheckinSerializer(checkin).data,
        "gut_score":   result.gut_score,
        "group_score": circle.group_gut_score,
        "created":     created,
    }, status=201 if created else 200)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def circle_jebena_today(request, circle_id):
    """GET /api/v1/community/circles/<id>/jebena/ — today's check-ins"""
    if not CircleMembership.objects.filter(
        circle_id=circle_id, user=request.user, is_active=True
    ).exists():
        return Response({"error": "Not a member."}, status=403)

    checkins = JebenaCheckin.objects.filter(
        circle_id=circle_id, date=date.today()
    ).select_related("user").order_by("-created_at")
    return Response(JebenaCheckinSerializer(checkins, many=True).data)


# ── Gursha Challenge ──────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_gursha(request):
    """
    POST /api/v1/community/gursha/send/
    { circle_id, to_username, food_slug, message? }
    """
    circle_id   = request.data.get("circle_id")
    to_username = request.data.get("to_username", "").strip()
    food_slug   = request.data.get("food_slug", "").strip()
    message     = request.data.get("message", "").strip()

    if not all([circle_id, to_username, food_slug]):
        return Response({"error": "circle_id, to_username and food_slug are required."}, status=400)

    try:
        circle  = WellnessCircle.objects.get(id=circle_id)
        to_user = User.objects.get(username=to_username)
    except (WellnessCircle.DoesNotExist, User.DoesNotExist):
        return Response({"error": "Circle or user not found."}, status=404)

    if to_user == request.user:
        return Response({"error": "You cannot send a Gursha to yourself."}, status=400)

    if not circle.memberships.filter(user=to_user, is_active=True).exists():
        return Response({"error": f"@{to_username} is not in this circle."}, status=400)

    from foods.models import EthiopianFood
    food = EthiopianFood.objects.filter(slug=food_slug).first()
    if not food:
        return Response({"error": "Food not found."}, status=404)

    gursha = GurshaChallenge.objects.create(
        from_user    = request.user,
        to_user      = to_user,
        circle       = circle,
        food_slug    = food.slug,
        food_name    = food.name_en.split(" — ")[0].split(" (")[0],
        food_name_am = food.name_am or "",
        message      = message,
        expires_at   = timezone.now() + timedelta(hours=24),
    )

    CircleMembership.objects.filter(
        circle=circle, user=request.user
    ).update(gursha_given=F("gursha_given") + 1)

    return Response(GurshaChallengeSerializer(gursha).data, status=201)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def accept_gursha(request, gursha_id):
    """POST /api/v1/community/gursha/<id>/accept/"""
    try:
        gursha = GurshaChallenge.objects.get(
            id=gursha_id, to_user=request.user, status="pending"
        )
    except GurshaChallenge.DoesNotExist:
        return Response({"error": "Gursha not found or already processed."}, status=404)

    if gursha.is_expired:
        gursha.status = "expired"
        gursha.save(update_fields=["status"])
        return Response({"error": "This Gursha has expired (24h limit)."}, status=400)

    gursha.status    = "accepted"
    gursha.points_to   = 15
    gursha.points_from = 10
    gursha.save()

    CircleMembership.objects.filter(
        circle=gursha.circle, user=request.user
    ).update(gursha_received=F("gursha_received") + 1)

    # Community post
    if gursha.circle.is_public:
        CommunityPost.objects.create(
            user      = gursha.to_user,
            circle    = gursha.circle,
            post_type = "gursha",
            title     = f"Accepted a Gursha from @{gursha.from_user.username}!",
            body      = f"Logged {gursha.food_name_am or gursha.food_name} and earned 15 points 🌿",
            emoji     = "🤝",
        )

    return Response({"ok": True, "points_earned": 15})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_gursha(request):
    """GET /api/v1/community/gursha/ — pending gursha for me"""
    pending = GurshaChallenge.objects.filter(
        to_user=request.user, status="pending"
    ).select_related("from_user", "circle").order_by("-created_at")
    return Response(GurshaChallengeSerializer(pending, many=True).data)


# ── Edir Fund ─────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def contribute_edir(request, circle_id):
    """
    POST /api/v1/community/circles/<id>/edir/
    { amount_etb: 50, note?: "..." }
    """
    try:
        circle = WellnessCircle.objects.get(
            id=circle_id,
            memberships__user=request.user,
            memberships__is_active=True,
        )
    except WellnessCircle.DoesNotExist:
        return Response({"error": "Circle not found."}, status=404)

    try:
        amount = Decimal(str(request.data.get("amount_etb", 0)))
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return Response({"error": "amount_etb must be a positive number."}, status=400)

    contribution = EdirContribution.objects.create(
        circle     = circle,
        user       = request.user,
        amount_etb = amount,
        note       = request.data.get("note", "").strip(),
    )

    circle.edir_balance_etb = (circle.edir_balance_etb or Decimal("0")) + amount
    circle.save(update_fields=["edir_balance_etb"])

    CircleMembership.objects.filter(
        circle=circle, user=request.user
    ).update(edir_contributed=F("edir_contributed") + amount)

    return Response({
        "contribution": EdirContributionSerializer(contribution).data,
        "new_balance":  float(circle.edir_balance_etb),
        "progress_pct": circle.edir_progress_pct,
        "goal_reached": circle.edir_progress_pct >= 100,
    }, status=201)


# ── Community Feed ────────────────────────────────────────────────────────────

class CommunityFeedView(generics.ListAPIView):
    """GET /api/v1/community/feed/"""
    serializer_class   = CommunityPostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CommunityPost.objects.select_related("user").order_by("-created_at")[:50]


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def like_post(request, post_id):
    """POST /api/v1/community/feed/<id>/like/"""
    try:
        post = CommunityPost.objects.get(id=post_id)
        post.likes = F("likes") + 1
        post.save(update_fields=["likes"])
        post.refresh_from_db()
        return Response({"likes": post.likes})
    except CommunityPost.DoesNotExist:
        return Response({"error": "Post not found."}, status=404)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _refresh_group_score(circle: WellnessCircle):
    scores = list(JebenaCheckin.objects.filter(
        circle=circle, date=date.today()
    ).values_list("gut_score", flat=True))
    if scores:
        circle.group_gut_score   = int(sum(scores) / len(scores))
        circle.total_meals_logged = (circle.total_meals_logged or 0) + 1
        circle.save(update_fields=["group_gut_score", "total_meals_logged"])


def _post_milestone(user, circle: WellnessCircle, score: int):
    profile = getattr(user, "profile", None)
    streak  = getattr(profile, "wellness_streak_days", 0) if profile else 0
    CommunityPost.objects.get_or_create(
        user=user, circle=circle, post_type="score",
        defaults={
            "title":  f"Scored {score}/100 today! 🌿",
            "body":   f"{streak}-day streak. Ethiopian gut health is real.",
            "emoji":  "🏆",
            "score":  score,
            "streak": streak,
        },
    )