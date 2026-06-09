"""community/serializers.py"""
import random, string
from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers
from .models import (
    WellnessCircle, CircleMembership, JebenaCheckin,
    GurshaChallenge, EdirContribution, CommunityPost,
)


def _make_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


class CircleMemberSerializer(serializers.ModelSerializer):
    username     = serializers.CharField(source="user.username", read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model  = CircleMembership
        fields = ["id","username","display_name","role","is_active",
                  "circle_gut_score","circle_streak","gursha_given","gursha_received","edir_contributed"]
        read_only_fields = fields

    def get_display_name(self, obj):
        return getattr(getattr(obj.user, "profile", None), "display_name", "") or ""


class WellnessCircleSerializer(serializers.ModelSerializer):
    member_count      = serializers.ReadOnlyField()
    edir_progress_pct = serializers.ReadOnlyField()
    members           = serializers.SerializerMethodField()
    is_member         = serializers.SerializerMethodField()
    my_role           = serializers.SerializerMethodField()

    class Meta:
        model  = WellnessCircle
        fields = ["id","name","name_am","description","emoji","invite_code",
                  "member_count","max_members","group_gut_score","group_streak_days",
                  "total_meals_logged","edir_balance_etb","edir_goal_etb",
                  "edir_target_pkg","edir_progress_pct","is_public",
                  "members","is_member","my_role","created_at"]
        read_only_fields = ["id","invite_code","group_gut_score","group_streak_days",
                            "total_meals_logged","edir_balance_etb","edir_progress_pct",
                            "members","is_member","my_role","created_at"]

    def get_members(self, obj):
        qs = obj.memberships.filter(is_active=True).select_related("user")
        return CircleMemberSerializer(qs, many=True).data

    def get_is_member(self, obj):
        req = self.context.get("request")
        return req and obj.memberships.filter(user=req.user, is_active=True).exists()

    def get_my_role(self, obj):
        req = self.context.get("request")
        if not req: return None
        m = obj.memberships.filter(user=req.user, is_active=True).first()
        return m.role if m else None

    def create(self, validated_data):
        validated_data["created_by"]  = self.context["request"].user
        validated_data["invite_code"] = _make_code()
        circle = super().create(validated_data)
        CircleMembership.objects.create(circle=circle, user=circle.created_by, role="admin")
        return circle


class JebenaCheckinSerializer(serializers.ModelSerializer):
    username     = serializers.CharField(source="user.username", read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model  = JebenaCheckin
        fields = ["id","username","display_name","food_slug","food_name",
                  "food_name_am","gut_score","message","mood_emoji","date","created_at"]
        read_only_fields = ["id","username","display_name","created_at"]

    def get_display_name(self, obj):
        return getattr(getattr(obj.user, "profile", None), "display_name", "") or ""


class GurshaChallengeSerializer(serializers.ModelSerializer):
    from_username = serializers.CharField(source="from_user.username", read_only=True)
    to_username   = serializers.CharField(source="to_user.username",   read_only=True)
    is_expired    = serializers.ReadOnlyField()

    class Meta:
        model  = GurshaChallenge
        fields = ["id","from_username","to_username","food_slug","food_name",
                  "food_name_am","message","status","expires_at","is_expired",
                  "points_from","points_to","created_at"]
        read_only_fields = ["id","from_username","to_username","status","expires_at",
                            "is_expired","points_from","points_to","created_at"]


class EdirContributionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model  = EdirContribution
        fields = ["id","username","amount_etb","note","is_confirmed","created_at"]
        read_only_fields = ["id","username","is_confirmed","created_at"]


class CommunityPostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model  = CommunityPost
        fields = ["id","author","post_type","title","body","emoji",
                  "score","streak","likes","created_at"]
        read_only_fields = ["id","author","likes","created_at"]

    def get_author(self, obj):
        if obj.is_anonymous:
            return {"username": "Anonymous member", "display_name": ""}
        return {
            "username":     obj.user.username,
            "display_name": getattr(getattr(obj.user, "profile", None), "display_name", "") or "",
        }