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
    # ── Circles ────────────────────────────────────────────────────
    path("circles/",
         MyCirclesView.as_view()),                          # GET list / POST create

    path("circles/join/",
         join_circle),                                      # POST { invite_code }

    path("circles/<uuid:pk>/",
         CircleDetailView.as_view()),                       # GET detail / PATCH update

    path("circles/<uuid:circle_id>/leave/",
         leave_circle),                                     # POST

    path("circles/<uuid:circle_id>/jebena/",
         circle_jebena_today),                              # GET today's check-ins

    path("circles/<uuid:circle_id>/edir/",
         contribute_edir),                                  # POST contribute

    # ── Jebena check-in ────────────────────────────────────────────
    path("jebena/",
         jebena_checkin),                                   # POST log food for circle

    # ── Gursha ─────────────────────────────────────────────────────
    path("gursha/",
         my_gursha),                                        # GET pending for me

    path("gursha/send/",
         send_gursha),                                      # POST send to member

    path("gursha/<uuid:gursha_id>/accept/",
         accept_gursha),                                    # POST accept

    # ── Community feed ─────────────────────────────────────────────
    path("feed/",
         CommunityFeedView.as_view()),                      # GET public posts

    path("feed/<uuid:post_id>/like/",
         like_post),                                        # POST like
]