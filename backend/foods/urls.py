# ── foods/urls.py ──

from django.urls import path
from .views import (
    FoodListView, FoodDetailView,
    log_meal, MealLogListView,
    dashboard_feed,  # ← 1. Import your new dashboard view
    daily_nutrition, weekly_nutrition,
)

urlpatterns = [
    path("",                    FoodListView.as_view()),
    path("log/",                log_meal),
    path("logs/",               MealLogListView.as_view()),
    path("feed/",               dashboard_feed),  # ← 2. Insert above slug route!
    path("daily/",              daily_nutrition),
    path("weekly/",             weekly_nutrition),
    path("<slug:slug>/",        FoodDetailView.as_view()),
]