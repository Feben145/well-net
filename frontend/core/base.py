"""
core/ — shared utilities used across all Well-Net apps.
Nothing business-logic here — pure infrastructure.
"""
import uuid
from django.db import models
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission


# ── Base Model ────────────────────────────────────────────────────────────────

class TimeStampedModel(models.Model):
    """
    Abstract base for every Well-Net model.
    Gives every table: uuid pk, created_at, updated_at.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ── Pagination ────────────────────────────────────────────────────────────────

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class SmallPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


# ── Permissions ───────────────────────────────────────────────────────────────

class IsOwner(BasePermission):
    """Allow access only to object owner."""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsVerifiedProfessional(BasePermission):
    """Allow access only to license-verified professionals."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, "professional_profile")
            and request.user.professional_profile.is_verified
        )


class IsKuriftuPartner(BasePermission):
    """Allow Kuriftu API to post off-peak deals."""
    def has_permission(self, request, view):
        from django.conf import settings
        token = request.headers.get("X-Kuriftu-Key", "")
        return token == settings.KURIFTU_API_KEY
