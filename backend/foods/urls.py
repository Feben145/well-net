"""foods/urls.py"""
from django.urls import path
from .views import (
    FoodListView, FoodDetailView,
    log_meal, MealLogListView,
    daily_nutrition, weekly_nutrition,
)

urlpatterns = [
    path("",                    FoodListView.as_view()),
    path("log/",                log_meal),           # ← moved up
    path("logs/",               MealLogListView.as_view()),
    path("daily/",              daily_nutrition),
    path("weekly/",             weekly_nutrition),
    path("<slug:slug>/",        FoodDetailView.as_view()),  # ← last
]