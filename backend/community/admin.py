"""community/admin.py — register models so you can inspect data in /admin/"""
from django.contrib import admin
from .models import (
    WellnessCircle,
    CircleMembership,
    JebenaCheckin,
    GurshaChallenge,
    EdirContribution,
    CommunityPost,
)


@admin.register(WellnessCircle)
class WellnessCircleAdmin(admin.ModelAdmin):
    list_display  = ["name", "invite_code", "member_count", "group_gut_score", "is_public", "created_at"]
    search_fields = ["name", "name_am", "invite_code"]
    readonly_fields = ["invite_code"]


@admin.register(CircleMembership)
class CircleMembershipAdmin(admin.ModelAdmin):
    list_display  = ["user", "circle", "role", "is_active", "circle_gut_score"]
    list_filter   = ["role", "is_active"]


@admin.register(JebenaCheckin)
class JebenaCheckinAdmin(admin.ModelAdmin):
    list_display  = ["user", "circle", "date", "food_name", "gut_score"]
    list_filter   = ["date"]


@admin.register(GurshaChallenge)
class GurshaChallengeAdmin(admin.ModelAdmin):
    list_display  = ["from_user", "to_user", "circle", "food_name", "status", "expires_at"]
    list_filter   = ["status"]


@admin.register(EdirContribution)
class EdirContributionAdmin(admin.ModelAdmin):
    list_display  = ["user", "circle", "amount_etb", "created_at"]


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display  = ["title", "user", "circle", "post_type", "likes", "created_at"]
    list_filter   = ["post_type", "is_anonymous"]
