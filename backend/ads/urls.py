"""ads/urls.py"""
from django.urls import path
from . import views

urlpatterns = [
    path("",              views.ad_list,   name="ad-list"),
    path("submit/",       views.ad_submit, name="ad-submit"),
    path("<uuid:ad_id>/click/", views.ad_click, name="ad-click"),
]