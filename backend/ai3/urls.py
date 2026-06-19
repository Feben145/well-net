"""ai/urls.py"""
from django.urls import path
from .views import (
    wellness_tips, generate_meal_plan,
    wellness_journey_feed, sms_webhook, telegram_webhook,
)

urlpatterns = [
    path("tips/",           wellness_tips),
    path("meal-plan/",      generate_meal_plan),
    path("feed/",           wellness_journey_feed),
    path("sms/",            sms_webhook),
    path("telegram/",       telegram_webhook),
]
