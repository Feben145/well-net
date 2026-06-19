"""community/serializers.py"""
from rest_framework import serializers
from .models import (
    WellnessCircle,
    CircleMembership,
    JebenaCheckin,
    GurshaChallenge,
    EdirContribution,
    CommunityPost,
)


def _display_name(user) -> str:
    profile = getattr(user, "profile", None)
    return getattr(profile, "display_name", "") or ""


# ── Circle member (nested inside circle) ───────────────────────────────────────

class CircleMemberSerializer(serializers.ModelSerializer):
    id               = serializers.CharField(read_only=True)
    username         = serializers.CharField(source="user.username", read_only=True)
    display_name     = serializers.SerializerMethodField()

    class Meta:
        model = CircleMembership
        fields = [
            "id", "username", "display_name", "role",
            "circle_gut_score", "gursha_given", "gursha_received", "edir_contributed",
        ]

    def get_display_name(self, obj):
        return _display_name(obj.user)


# ── Wellness Circle ────────────────────────────────────────────────────────────

class WellnessCircleSerializer(serializers.ModelSerializer):
    member_count      = serializers.IntegerField(read_only=True)
    edir_progress_pct = serializers.IntegerField(read_only=True)
    members           = serializers.SerializerMethodField()
    is_member         = serializers.SerializerMethodField()
    my_role           = serializers.SerializerMethodField()

    class Meta:
        model = WellnessCircle
        fields = [
            "id", "name", "name_am", "description", "emoji", "invite_code",
            "member_count", "max_members",
            "group_gut_score", "group_streak_days",
            "edir_balance_etb", "edir_goal_etb", "edir_progress_pct", "edir_target_pkg",
            "members", "is_member", "my_role", "is_public",
            "created_at",
        ]
        read_only_fields = ["id", "invite_code", "created_at"]

    def get_members(self, obj):
        qs = obj.memberships.filter(is_active=True).select_related("user")
        return CircleMemberSerializer(qs, many=True).data

    def get_is_member(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.memberships.filter(user=request.user, is_active=True).exists()

    def get_my_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user, is_active=True).first()
        return membership.role if membership else None


class CreateCircleSerializer(serializers.ModelSerializer):
    """
    Input-only serializer used for POST /circles/.
    Accepts: name, name_am, description, emoji, is_public, max_members
    invite_code is generated server-side. created_by comes from request.user.
    """
    class Meta:
        model = WellnessCircle
        fields = ["name", "name_am", "description", "emoji", "is_public", "max_members"]

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Circle name is required.")
        return value


# ── Jebena ────────────────────────────────────────────────────────────────────

class JebenaCheckinSerializer(serializers.ModelSerializer):
    username     = serializers.CharField(source="user.username", read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = JebenaCheckin
        fields = [
            "id", "username", "display_name",
            "food_slug", "food_name", "food_name_am",
            "gut_score", "message", "mood_emoji", "date", "created_at",
        ]

    def get_display_name(self, obj):
        return _display_name(obj.user)


# ── Gursha ────────────────────────────────────────────────────────────────────

class GurshaChallengeSerializer(serializers.ModelSerializer):
    from_username = serializers.CharField(source="from_user.username", read_only=True)
    is_expired    = serializers.BooleanField(read_only=True)

    class Meta:
        model = GurshaChallenge
        fields = [
            "id", "from_username",
            "food_slug", "food_name", "food_name_am",
            "message", "status", "expires_at", "is_expired",
            "points_from", "points_to", "created_at",
        ]


# ── Edir ──────────────────────────────────────────────────────────────────────

class EdirContributionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = EdirContribution
        fields = ["id", "username", "amount_etb", "note", "is_confirmed", "created_at"]


# ── Community Feed ────────────────────────────────────────────────────────────

class CommunityPostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = CommunityPost
        fields = ["id", "author", "post_type", "title", "body", "emoji", "score", "streak", "likes", "created_at"]

    def get_author(self, obj):
        if obj.is_anonymous:
            return {"username": "anonymous", "display_name": "Anonymous member"}
        return {
            "username":     obj.user.username,
            "display_name": _display_name(obj.user),
        }
