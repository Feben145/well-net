"""users/urls.py"""
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, MeView, ProfileView,
    FamilyMemberListCreateView, FamilyMemberDetailView,
)

urlpatterns = [
    path("register/",           RegisterView.as_view()),
    path("login/",              TokenObtainPairView.as_view()),
    path("token/refresh/",      TokenRefreshView.as_view()),
    path("me/",                 MeView.as_view()),
    path("profile/",            ProfileView.as_view()),
    path("family/",             FamilyMemberListCreateView.as_view()),
    path("family/<uuid:pk>/",   FamilyMemberDetailView.as_view()),
]
