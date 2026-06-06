"""notifications/tasks.py — Celery background tasks"""
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@shared_task
def send_daily_wellness_tip():
    """
    Runs at 8 AM Addis Ababa time (configured in settings.CELERY_BEAT_SCHEDULE).
    Sends a personalised daily wellness tip to all users with SMS enabled.
    """
    from foods.models import DailyNutrition
    from datetime import date, timedelta

    yesterday = date.today() - timedelta(days=1)
    users = User.objects.filter(sms_notifications=True, phone__isnull=False).exclude(phone="")

    for user in users:
        try:
            score = 0
            try:
                dn = DailyNutrition.objects.get(user=user, date=yesterday)
                score = dn.gut_score
            except DailyNutrition.DoesNotExist:
                pass

            tip = _get_daily_tip(score)
            message = f"Selam! Well-Net daily:\n\nYesterday score: {score}/100\n\n{tip}\n\nReply TIPS or log: wellnet.et"
            _send_sms(user.phone, message)
            _log_notification(user, "daily_tip", "Daily wellness tip", message)
        except Exception:
            pass


@shared_task
def send_offpeak_deals():
    """
    Runs every 2 hours. Matches active Kuriftu deals to eligible users.
    """
    from notifications.models import OffPeakDeal, Notification
    from datetime import timedelta

    now = timezone.now()
    active_deals = OffPeakDeal.objects.filter(
        is_active=True,
        valid_from__lte=now + timedelta(hours=24),
        valid_until__gte=now,
        slots_booked__lt=models.F("slots_available"),
    )

    for deal in active_deals:
        # Target users whose gut score matches the deal's range
        eligible_users = User.objects.filter(
            sms_notifications=True,
            phone__isnull=False,
            profile__current_gut_score__gte=deal.min_gut_score,
            profile__current_gut_score__lte=deal.max_gut_score,
        ).exclude(phone="")

        # Don't re-send to users who already got this deal notification today
        already_sent = Notification.objects.filter(
            deal=deal,
            sent_at__date=now.date(),
        ).values_list("user_id", flat=True)

        eligible_users = eligible_users.exclude(id__in=already_sent)

        for user in eligible_users[:50]:  # cap at 50 per batch
            try:
                message = (
                    f"Well-Net × Kuriftu Deal:\n\n"
                    f"{deal.title}\n"
                    f"{deal.location}\n"
                    f"{deal.discounted_price_etb} ETB (was {deal.original_price_etb} ETB — {deal.discount_pct}% off)\n"
                    f"{deal.slots_remaining} slots left\n\n"
                    f"Book: {deal.booking_url or 'kurifturesorts.com'}\n"
                    f"Valid until: {deal.valid_until.strftime('%b %d %I:%M%p')}"
                )
                _send_sms(user.phone, message)
                _log_notification(user, "off_peak_deal", deal.title, message, deal=deal)
            except Exception:
                pass


@shared_task
def send_weekly_report():
    """
    Runs weekly. Sends a 'Wellness Wrapped' summary to each user.
    """
    from foods.models import DailyNutrition
    from datetime import date, timedelta

    today = date.today()
    seven_ago = today - timedelta(days=6)

    users = User.objects.filter(sms_notifications=True).exclude(phone="")

    for user in users:
        try:
            records = DailyNutrition.objects.filter(
                user=user, date__gte=seven_ago, date__lte=today
            )
            if not records.exists():
                continue

            avg = round(sum(r.gut_score for r in records) / records.count())
            best = max(records, key=lambda r: r.gut_score)
            streak = getattr(getattr(user, "profile", None), "wellness_streak_days", 0)

            message = (
                f"Well-Net Weekly Report:\n\n"
                f"Avg gut score: {avg}/100\n"
                f"Best day: {best.date.strftime('%A')} ({best.gut_score})\n"
                f"Streak: {streak} days\n\n"
                f"Top tip: Add fermented injera and misir wot daily — "
                f"users who do improve by 12pts in 2 weeks.\n\n"
                f"See full report: wellnet.et/dashboard"
            )
            _send_sms(user.phone, message)
            _log_notification(user, "weekly_report", "Your weekly wellness report", message)
        except Exception:
            pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _send_sms(phone: str, message: str):
    """Send SMS via Africa's Talking."""
    from django.conf import settings
    try:
        import africastalking
        africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
        sms = africastalking.SMS
        sms.send(message, [phone])
    except Exception as e:
        print(f"SMS send failed: {e}")


def _log_notification(user, notif_type: str, title: str, body: str, deal=None):
    from notifications.models import Notification
    Notification.objects.create(
        user=user,
        channel="sms",
        notif_type=notif_type,
        title=title,
        body=body,
        deal=deal,
    )


def _get_daily_tip(score: int) -> str:
    if score >= 80:
        return "Excellent gut health! Keep up your injera + legume combo. Your fermentation score is your superpower."
    if score >= 65:
        return "Great work! Add ayib or ergo today to boost your fermentation score."
    if score >= 50:
        return "Good start! Misir wot for lunch today will add prebiotic fiber and push your score higher."
    return "Let's boost your gut today! Start with teff porridge for breakfast — high fiber, low GI, big impact."
