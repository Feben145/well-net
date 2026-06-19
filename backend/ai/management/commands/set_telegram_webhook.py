"""
ai/management/commands/set_telegram_webhook.py

Usage:
  python manage.py set_telegram_webhook https://yourapp.up.railway.app

What it does:
  Registers your Django endpoint with Telegram so messages flow to your app.
  Only needs to run ONCE per deployment. Re-run if you change your domain.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import requests


class Command(BaseCommand):
    help = "Register the Telegram bot webhook with your deployed URL"

    def add_arguments(self, parser):
        parser.add_argument(
            "base_url",
            type=str,
            help="Your deployed base URL, e.g. https://yourapp.up.railway.app",
        )

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stdout.write(self.style.ERROR(
                "TELEGRAM_BOT_TOKEN not set in .env — add it first"
            ))
            return

        base_url    = options["base_url"].rstrip("/")
        webhook_url = f"{base_url}/api/v1/ai/telegram/"

        self.stdout.write(f"Setting webhook to: {webhook_url}")

        response = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": webhook_url, "allowed_updates": ["message", "callback_query"]},
            timeout=10,
        )
        result = response.json()

        if result.get("ok"):
            self.stdout.write(self.style.SUCCESS(
                f"Webhook set successfully!\n"
                f"Telegram will now POST updates to: {webhook_url}\n\n"
                f"Test it: open Telegram, find your bot, send /start"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"Failed: {result.get('description', 'Unknown error')}"
            ))


