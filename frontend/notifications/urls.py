"""notifications/urls.py"""
from django.urls import path
from .views import ActiveDealsView, NotificationHistoryView, create_deal

urlpatterns = [
    path("deals/",          ActiveDealsView.as_view()),
    path("deals/create/",   create_deal),
    path("history/",        NotificationHistoryView.as_view()),
]
