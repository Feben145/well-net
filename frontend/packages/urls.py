from django.urls import path
from .models import PackageListView, MySubscriptionsView

urlpatterns = [
    path("",     PackageListView.as_view()),
    path("my/",  MySubscriptionsView.as_view()),
]
