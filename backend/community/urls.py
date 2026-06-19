"""community/urls.py"""
from django.urls import path
from .views import (
    MyCirclesView, CircleDetailView,
    join_circle, leave_circle,
    jebena_checkin, circle_jebena_today,
    send_gursha, accept_gursha, my_gursha,
    contribute_edir,
    CommunityFeedView, like_post,
)

urlpatterns = [
    # Circles
    path("circles/",                         MyCirclesView.as_view()),
    path("circles/join/",                    join_circle),
    path("circles/<uuid:id>/",               CircleDetailView.as_view()),
    path("circles/<uuid:circle_id>/leave/",  leave_circle),
    path("circles/<uuid:circle_id>/jebena/", circle_jebena_today),
    path("circles/<uuid:circle_id>/edir/",   contribute_edir),

    # Jebena
    path("jebena/", jebena_checkin),

    # Gursha
    path("gursha/",                        my_gursha),
    path("gursha/send/",                   send_gursha),
    path("gursha/<uuid:gursha_id>/accept/", accept_gursha),

    # Feed
    path("feed/",                  CommunityFeedView.as_view()),
    path("feed/<uuid:post_id>/like/", like_post),
]
