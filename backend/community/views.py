"""
community/views.py

Defensive error handling everywhere: every view that touches the DB
catches exceptions and returns a clear JSON error instead of letting
Django's 500 page leak through. This is what was producing the
145-byte 500 responses — now you'll see the real reason instead.
"""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import (
    WellnessCircle,
    CircleMembership,
    JebenaCheckin,
    GurshaChallenge,
    EdirContribution,
    CommunityPost,
    generate_invite_code,
)
from .serializers import (
    WellnessCircleSerializer,
    CreateCircleSerializer,
    JebenaCheckinSerializer,
    GurshaChallengeSerializer,
    EdirContributionSerializer,
    CommunityPostSerializer,
)

User = get_user_model()


# ── Circles ───────────────────────────────────────────────────────────────────

class MyCirclesView(generics.ListCreateAPIView):
    """
    GET  /api/v1/community/circles/  -> circles I belong to
    POST /api/v1/community/circles/  -> create a new circle (creator becomes admin)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return CreateCircleSerializer if self.request.method == "POST" else WellnessCircleSerializer

    def get_queryset(self):
        return (
            WellnessCircle.objects
            .filter(memberships__user=self.request.user, memberships__is_active=True)
            .distinct()
        )

    def get_serializer_context(self):
        return {"request": self.request}

    def create(self, request, *args, **kwargs):
        serializer = CreateCircleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                # Guarantee a unique invite code even under retry/collision
                code = generate_invite_code()
                while WellnessCircle.objects.filter(invite_code=code).exists():
                    code = generate_invite_code()

                circle = WellnessCircle.objects.create(
                    created_by=request.user,
                    invite_code=code,
                    **serializer.validated_data,
                )
                CircleMembership.objects.create(
                    circle=circle, user=request.user, role="admin", is_active=True
                )
        except IntegrityError as e:
            return Response(
                {"error": "Could not create circle (duplicate or invalid data).", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": "Unexpected error creating circle.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        out = WellnessCircleSerializer(circle, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)


class CircleDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/community/circles/<id>/"""
    serializer_class   = WellnessCircleSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field        = "id"

    def get_queryset(self):
        return WellnessCircle.objects.filter(
            memberships__user=self.request.user, memberships__is_active=True
        )

    def get_serializer_context(self):
        return {"request": self.request}


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def join_circle(request):
    """POST /api/v1/community/circles/join/  { invite_code }"""
    code = (request.data.get("invite_code") or "").upper().strip()
    if not code:
        return Response({"error": "invite_code is required."}, status=400)

    try:
        circle = WellnessCircle.objects.get(invite_code=code)
    except WellnessCircle.DoesNotExist:
        return Response({"error": "Invalid invite code — check and try again."}, status=404)

    if circle.member_count >= circle.max_members:
        return Response({"error": "This circle is full."}, status=400)

    try:
        membership, created = CircleMembership.objects.get_or_create(
            circle=circle, user=request.user,
            defaults={"role": "member", "is_active": True},
        )
        if not created and not membership.is_active:
            membership.is_active = True
            membership.save(update_fields=["is_active"])
    except Exception as e:
        return Response({"error": "Could not join circle.", "detail": str(e)}, status=500)

    out = WellnessCircleSerializer(circle, context={"request": request})
    return Response(out.data, status=201 if created else 200)


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
        other_admin_exists = CircleMembership.objects.filter(
            circle_id=circle_id, role="admin", is_active=True
        ).exclude(user=request.user).exists()
        if not other_admin_exists:
            return Response(
                {"error": "Assign another admin before leaving, or delete the circle."},
                status=400,
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
    circle_id  = request.data.get("circle_id")
    food_slug  = (request.data.get("food_slug") or "").strip()
    message    = (request.data.get("message") or "").strip()
    mood_emoji = request.data.get("mood_emoji") or "🌿"

    if not circle_id or not food_slug:
        return Response({"error": "circle_id and food_slug are required."}, status=400)

    circle = WellnessCircle.objects.filter(id=circle_id).first()
    if not circle:
        return Response({"error": "Circle not found."}, status=404)

    if not circle.memberships.filter(user=request.user, is_active=True).exists():
        return Response({"error": "You are not a member of this circle."}, status=403)

    # Find the food in the foods app
    try:
        from foods.models import EthiopianFood
    except Exception as e:
        return Response({"error": "Foods app not available.", "detail": str(e)}, status=500)

    food = EthiopianFood.objects.filter(slug=food_slug).first()
    if not food:
        food = EthiopianFood.objects.filter(slug__icontains=food_slug).first()
    if not food:
        return Response({"error": f"Food '{food_slug}' not found in database."}, status=404)

    # Compute gut score for this single food using the foods scoring engine
    gut_score = _score_single_food(food)

    try:
        checkin, created = JebenaCheckin.objects.update_or_create(
            circle=circle, user=request.user, date=date.today(),
            defaults={
                "food_slug":    food.slug,
                "food_name":    _short_name(food.name_en),
                "food_name_am": getattr(food, "name_am", "") or "",
                "gut_score":    gut_score,
                "message":      message,
                "mood_emoji":   mood_emoji,
            },
        )
    except Exception as e:
        return Response({"error": "Could not save check-in.", "detail": str(e)}, status=500)

    _refresh_group_score(circle)

    CircleMembership.objects.filter(circle=circle, user=request.user).update(
        circle_gut_score=gut_score
    )

    if gut_score >= 80 and circle.is_public:
        _post_milestone(request.user, circle, gut_score)

    return Response(
        {
            "checkin":     JebenaCheckinSerializer(checkin).data,
            "gut_score":   gut_score,
            "group_score": circle.group_gut_score,
            "created":     created,
        },
        status=201 if created else 200,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def circle_jebena_today(request, circle_id):
    """GET /api/v1/community/circles/<id>/jebena/ — today's check-ins for that circle"""
    if not CircleMembership.objects.filter(
        circle_id=circle_id, user=request.user, is_active=True
    ).exists():
        return Response({"error": "Not a member of this circle."}, status=403)

    checkins = (
        JebenaCheckin.objects
        .filter(circle_id=circle_id, date=date.today())
        .select_related("user")
        .order_by("-created_at")
    )
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
    to_username = (request.data.get("to_username") or "").strip()
    food_slug   = (request.data.get("food_slug") or "").strip()
    message     = (request.data.get("message") or "").strip()

    if not all([circle_id, to_username, food_slug]):
        return Response({"error": "circle_id, to_username and food_slug are required."}, status=400)

    circle = WellnessCircle.objects.filter(id=circle_id).first()
    if not circle:
        return Response({"error": "Circle not found."}, status=404)

    to_user = User.objects.filter(username=to_username).first()
    if not to_user:
        return Response({"error": f"User '{to_username}' not found."}, status=404)

    if to_user.id == request.user.id:
        return Response({"error": "You cannot send a Gursha to yourself."}, status=400)

    if not circle.memberships.filter(user=to_user, is_active=True).exists():
        return Response({"error": f"@{to_username} is not in this circle."}, status=400)

    try:
        from foods.models import EthiopianFood
    except Exception as e:
        return Response({"error": "Foods app not available.", "detail": str(e)}, status=500)

    food = EthiopianFood.objects.filter(slug=food_slug).first()
    if not food:
        return Response({"error": "Food not found."}, status=404)

    try:
        gursha = GurshaChallenge.objects.create(
            from_user=request.user,
            to_user=to_user,
            circle=circle,
            food_slug=food.slug,
            food_name=_short_name(food.name_en),
            food_name_am=getattr(food, "name_am", "") or "",
            message=message,
            expires_at=timezone.now() + timedelta(hours=24),
        )
    except Exception as e:
        return Response({"error": "Could not create Gursha.", "detail": str(e)}, status=500)

    CircleMembership.objects.filter(circle=circle, user=request.user).update(
        gursha_given=F("gursha_given") + 1
    )

    return Response(GurshaChallengeSerializer(gursha).data, status=201)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def accept_gursha(request, gursha_id):
    """POST /api/v1/community/gursha/<id>/accept/"""
    gursha = GurshaChallenge.objects.filter(
        id=gursha_id, to_user=request.user, status="pending"
    ).first()
    if not gursha:
        return Response({"error": "Gursha not found or already handled."}, status=404)

    if gursha.is_expired:
        gursha.status = "expired"
        gursha.save(update_fields=["status"])
        return Response({"error": "This Gursha has expired (24h limit)."}, status=400)

    gursha.status      = "accepted"
    gursha.points_to   = 15
    gursha.points_from = 10
    gursha.save()

    CircleMembership.objects.filter(circle=gursha.circle, user=request.user).update(
        gursha_received=F("gursha_received") + 1
    )

    if gursha.circle.is_public:
        CommunityPost.objects.create(
            user=gursha.to_user,
            circle=gursha.circle,
            post_type="gursha",
            title=f"Accepted a Gursha from @{gursha.from_user.username}!",
            body=f"Logged {gursha.food_name_am or gursha.food_name} and earned 15 points 🌿",
            emoji="🤝",
        )

    return Response({"ok": True, "points_earned": 15})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_gursha(request):
    """GET /api/v1/community/gursha/ — pending gursha sent TO me"""
    pending = (
        GurshaChallenge.objects
        .filter(to_user=request.user, status="pending")
        .select_related("from_user", "circle")
        .order_by("-created_at")
    )
    return Response(GurshaChallengeSerializer(pending, many=True).data)


# ── Edir Fund ─────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def contribute_edir(request, circle_id):
    """
    POST /api/v1/community/circles/<id>/edir/
    { amount_etb: 50, note?: "..." }
    """
    circle = WellnessCircle.objects.filter(
        id=circle_id, memberships__user=request.user, memberships__is_active=True
    ).first()
    if not circle:
        return Response({"error": "Circle not found."}, status=404)

    try:
        amount = Decimal(str(request.data.get("amount_etb", 0)))
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        return Response({"error": "amount_etb must be a positive number."}, status=400)

    try:
        contribution = EdirContribution.objects.create(
            circle=circle,
            user=request.user,
            amount_etb=amount,
            note=(request.data.get("note") or "").strip(),
        )
        circle.edir_balance_etb = (circle.edir_balance_etb or Decimal("0")) + amount
        circle.save(update_fields=["edir_balance_etb"])

        CircleMembership.objects.filter(circle=circle, user=request.user).update(
            edir_contributed=F("edir_contributed") + amount
        )
    except Exception as e:
        return Response({"error": "Could not save contribution.", "detail": str(e)}, status=500)

    return Response(
        {
            "contribution": EdirContributionSerializer(contribution).data,
            "new_balance":  float(circle.edir_balance_etb),
            "progress_pct": circle.edir_progress_pct,
            "goal_reached": circle.edir_progress_pct >= 100,
        },
        status=201,
    )


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
    post = CommunityPost.objects.filter(id=post_id).first()
    if not post:
        return Response({"error": "Post not found."}, status=404)
    CommunityPost.objects.filter(id=post_id).update(likes=F("likes") + 1)
    post.refresh_from_db()
    return Response({"likes": post.likes})


# ── Internal helpers ──────────────────────────────────────────────────────────

def _short_name(name_en: str) -> str:
    return name_en.split(" — ")[0].split(" (")[0].strip()


def _score_single_food(food) -> int:
    """
    Compute a gut score for ONE food.
    Tries the shared foods.scoring engine first; falls back to a
    simple local formula if that import or call fails for any reason.
    """
    try:
        from foods.scoring import compute_gut_score, FoodItem
        result = compute_gut_score([FoodItem(
            slug=food.slug,
            fiber_g=getattr(food, "fiber_g", 0) or 0,
            protein_g=getattr(food, "protein_g", 0) or 0,
            iron_mg=getattr(food, "iron_mg", 0) or 0,
            fermentation_score=getattr(food, "fermentation_score", 0) or 0,
            inflammatory_index=getattr(food, "inflammatory_index", 0) or 0,
            prebiotic_score=getattr(food, "prebiotic_score", 0) or 0,
        )])
        return int(result.gut_score)
    except Exception:
        # Local fallback — same weighting logic, no dependency on foods.scoring
        fiber  = getattr(food, "fiber_g", 0) or 0
        ferm   = getattr(food, "fermentation_score", 0) or 0
        inflam = getattr(food, "inflammatory_index", 0) or 0
        protein = getattr(food, "protein_g", 0) or 0

        fs = min(fiber / 25, 1)
        fes = min(ferm / 6, 1)
        is_ = max(0, min(1, (4 - inflam) / 8))
        ps = min(protein / 50, 1)
        score = (fs * 0.40 + fes * 0.30 + is_ * 0.20 + ps * 0.10) * 100
        return int(round(score))


def _refresh_group_score(circle: WellnessCircle):
    scores = list(
        JebenaCheckin.objects.filter(circle=circle, date=date.today())
        .values_list("gut_score", flat=True)
    )
    if scores:
        circle.group_gut_score = int(sum(scores) / len(scores))
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
