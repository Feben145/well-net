"""experts/urls.py"""
from django.urls import path
from .views import ProfessionalListView, book_session, MySessionsView

urlpatterns = [
    path("",                          ProfessionalListView.as_view()),
    path("<uuid:professional_id>/book/", book_session),
    path("my-sessions/",              MySessionsView.as_view()),
]
