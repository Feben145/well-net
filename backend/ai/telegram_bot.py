"""
ai/telegram_bot.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Well-Net Telegram Bot — full upgrade

How it works:
  1. User messages the bot
  2. Telegram sends a POST to /api/v1/ai/telegram/
  3. This module processes the update
  4. Replies with text + inline keyboards where useful

Two types of incoming updates:
  - message: user typed something
  - callback_query: user tapped an inline button
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import requests
from django.conf import settings

# ── Sender helpers ────────────────────────────────────────────────────────────

def send_message(chat_id: int, text: str, reply_markup: dict | None = None):
    """Send a plain text message, optionally with inline keyboard."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",          # lets us use <b>, <i> in replies
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=8,
        )
    except Exception:
        pass


def answer_callback(callback_id: str, text: str = ""):
    """Must acknowledge every callback_query or Telegram shows a loading spinner."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": text},
            timeout=5,
        )
    except Exception:
        pass


# ── Inline keyboard builders ──────────────────────────────────────────────────

def main_menu_keyboard() -> dict:
    """Main quick-action keyboard shown after /start and unknown input."""
    return {
        "inline_keyboard": [
            [
                {"text": "🌿 Log foods & get score",  "callback_data": "cmd_log"},
                {"text": "💡 Wellness tips",          "callback_data": "cmd_tips"},
            ],
            [
                {"text": "🏨 Kuriftu deals",          "callback_data": "cmd_kuriftu"},
                {"text": "👨‍⚕️ Find an expert",      "callback_data": "cmd_expert"},
            ],
            [
                {"text": "👨‍👩‍👧 Family planner",  "callback_data": "cmd_family"},
                {"text": "📊 My score",               "callback_data": "cmd_score"},
            ],
        ]
    }


def food_category_keyboard() -> dict:
    """Let user pick a food category to log."""
    return {
        "inline_keyboard": [
            [
                {"text": "🌾 Grains (injera, teff)",    "callback_data": "cat_grains"},
                {"text": "🫘 Legumes (misir, shiro)",   "callback_data": "cat_legumes"},
            ],
            [
                {"text": "🍖 Meat (tibs, kitfo, doro)", "callback_data": "cat_meat"},
                {"text": "🥛 Dairy (ayib, ergo)",       "callback_data": "cat_dairy"},
            ],
            [
                {"text": "🥦 Vegetables (gomen)",       "callback_data": "cat_veg"},
                {"text": "☕ Drinks (buna, tej)",        "callback_data": "cat_drinks"},
            ],
            [
                {"text": "← Back to menu",              "callback_data": "cmd_menu"},
            ],
        ]
    }


def kuriftu_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "🌐 Book at kurifturesorts.com", "url": "https://kurifturesorts.com"}],
            [{"text": "🏋️ Wellness packages",          "callback_data": "cmd_packages"}],
            [{"text": "← Back",                        "callback_data": "cmd_menu"}],
        ]
    }


def back_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "← Main menu", "callback_data": "cmd_menu"}]
        ]
    }


# ── Message router ────────────────────────────────────────────────────────────

def handle_message(chat_id: int, text: str, user_first_name: str = ""):
    """Route an incoming text message to the right reply."""
    t = text.strip().lower()

    # Commands
    if t in ("/start", "start"):
        handle_start(chat_id, user_first_name)
        return

    if t in ("/help", "help"):
        send_message(chat_id, HELP_TEXT, back_keyboard())
        return

    if t in ("/menu", "menu"):
        send_message(chat_id, "What would you like to do?", main_menu_keyboard())
        return

    # Food keywords → score
    from ai.views import FOOD_KEYWORDS, _score_from_text
    if any(kw in t for kw in FOOD_KEYWORDS):
        reply = _score_from_text(t)
        send_message(chat_id, reply, back_keyboard())
        return

    # Intent keywords
    if any(kw in t for kw in ["tip", "tips", "advice"]):
        send_message(chat_id, _tips_message(), back_keyboard())
        return

    if any(kw in t for kw in ["kuriftu", "resort", "spa", "retreat", "yoga"]):
        send_message(chat_id, _kuriftu_message(), kuriftu_keyboard())
        return

    if any(kw in t for kw in ["expert", "doctor", "nutritionist", "dietitian"]):
        send_message(chat_id, _expert_message(), back_keyboard())
        return

    if any(kw in t for kw in ["score", "gut", "health", "status"]):
        send_message(chat_id, _score_prompt(), food_category_keyboard())
        return

    # Unknown → show menu
    send_message(
        chat_id,
        f"Selam! 🌿 I didn't understand that.\n\nTry texting the foods you ate — for example:\n<b>injera misir ayib</b>\n\nOr choose from the menu below:",
        main_menu_keyboard(),
    )


def handle_callback(chat_id: int, callback_id: str, data: str, user_first_name: str = ""):
    """Handle inline button taps."""
    # Always acknowledge first
    answer_callback(callback_id)

    if data == "cmd_menu":
        send_message(chat_id, "What would you like to do?", main_menu_keyboard())

    elif data == "cmd_log":
        send_message(
            chat_id,
            "🌾 <b>Log your meal</b>\n\nText me the Ethiopian foods you ate today.\n\nExamples:\n• <code>injera misir tej</code>\n• <code>shiro tibs ayib</code>\n• <code>teff porridge buna</code>\n\nOr pick a category:",
            food_category_keyboard(),
        )

    elif data == "cmd_tips":
        send_message(chat_id, _tips_message(), back_keyboard())

    elif data == "cmd_kuriftu":
        send_message(chat_id, _kuriftu_message(), kuriftu_keyboard())

    elif data == "cmd_expert":
        send_message(chat_id, _expert_message(), back_keyboard())

    elif data == "cmd_family":
        send_message(chat_id, _family_message(), back_keyboard())

    elif data == "cmd_score":
        send_message(chat_id, _score_prompt(), food_category_keyboard())

    elif data == "cmd_packages":
        send_message(chat_id, _packages_message(), back_keyboard())

    elif data.startswith("cat_"):
        category = data.replace("cat_", "")
        send_message(chat_id, _category_foods(category), back_keyboard())

    else:
        send_message(chat_id, "Coming soon!", back_keyboard())


# ── Start message ─────────────────────────────────────────────────────────────

def handle_start(chat_id: int, name: str = ""):
    greeting = f"Selam{', ' + name if name else ''}! 👋" 
    msg = (
        f"{greeting}\n\n"
        f"Welcome to <b>Well-Net</b> — Ethiopian Wellness Ecosystem.\n\n"
        f"I'm <b>Hana</b>, your AI wellness coach. I understand Ethiopian food better than any other app.\n\n"
        f"🌿 Tell me what you ate and I'll score your gut health\n"
        f"🏨 Find Kuriftu wellness experiences matched to your score\n"
        f"👨‍⚕️ Book a licensed Ethiopian nutritionist\n"
        f"👨‍👩‍👧 Plan meals for your whole family\n\n"
        f"<b>Try it now:</b> Just type the foods you ate today\n"
        f"Example: <code>injera misir ayib tej</code>"
    )
    send_message(chat_id, msg, main_menu_keyboard())


# ── Reply content ─────────────────────────────────────────────────────────────

def _tips_message() -> str:
    return (
        "🌿 <b>3 Well-Net Gut Health Tips</b>\n\n"
        "1️⃣ <b>Injera daily</b>\n"
        "   Teff is one of the most fiber-rich grains on earth. Fermentation adds natural probiotics.\n\n"
        "2️⃣ <b>Misir wot 3× a week</b>\n"
        "   Glycemic index = 19 (one of the lowest of any Ethiopian dish). Lentil fiber feeds your gut bacteria.\n\n"
        "3️⃣ <b>Add ayib or ergo</b>\n"
        "   Natural Ethiopian fermented dairy. Your gut microbiome will thank you in 2 weeks.\n\n"
        "📱 Log your meals on Well-Net for personalised AI tips from Hana."
    )


def _kuriftu_message() -> str:
    return (
        "🏨 <b>Kuriftu × Well-Net Wellness</b>\n\n"
        "As a Well-Net partner, Kuriftu offers:\n\n"
        "✦ <b>Gut Health Passport</b> — scan QR at check-in, get your score in 60 seconds\n"
        "✦ <b>Yoga sessions</b> — with Weini and Christine (Iyengar + mat pilates)\n"
        "✦ <b>Mystic Nights</b> — overnight sound healing and meditation\n"
        "✦ <b>Personalised menu scoring</b> — every dish rated for gut health\n"
        "✦ <b>Boston Day Spa</b> — gut-targeted treatments matched to your score\n\n"
        "📍 Locations: Bishoftu · African Village · Lake Tana · Awash · Entoto"
    )


def _expert_message() -> str:
    return (
        "👨‍⚕️ <b>Licensed Ethiopian Wellness Experts</b>\n\n"
        "Well-Net connects you with MOH and FMHACA-verified professionals:\n\n"
        "• Registered Dietitians (RD)\n"
        "• Certified Nutrition Specialists\n"
        "• Gastroenterologists\n"
        "• Kuriftu wellness coaches\n"
        "• Yoga instructors\n\n"
        "Sessions from <b>280 ETB</b> · Video, in-person, or group\n"
        "Off-peak slots available at discount.\n\n"
        "📱 Book via the Well-Net app: wellnet.et/experts"
    )


def _family_message() -> str:
    return (
        "👨‍👩‍👧 <b>Family Wellness Planner</b>\n\n"
        "Track gut health for your whole family — up to 6 profiles:\n\n"
        "• Adults, children, elders, pregnant members\n"
        "• Personalised meal suggestions per member\n"
        "• Pregnancy-safe and fasting-safe filters\n"
        "• AI generates a 7-day family meal plan\n"
        "• Alerts when a family member's score is low\n\n"
        "📱 Set up your family plan: wellnet.et/family"
    )


def _packages_message() -> str:
    return (
        "📦 <b>Well-Net Wellness Packages</b>\n\n"
        "🌿 <b>Individual</b> — 150 ETB/month\n"
        "   Daily scores · AI tips · SMS reminders\n\n"
        "👨‍👩‍👧 <b>Family</b> — 450 ETB/month\n"
        "   6 profiles · Meal plans · Nutritionist consult\n\n"
        "🏨 <b>Kuriftu Resort Bundle</b> — 1,800 ETB\n"
        "   QR check-in · Spa treatment · 30-day follow-up\n\n"
        "👥 <b>Group / Friends</b> — 200 ETB/person (min 4)\n"
        "   Group gut scan · Shared leaderboard · Kuriftu 25% off\n\n"
        "🏢 <b>Corporate</b> — 500 ETB/employee/year\n"
        "   Dashboard · HR reports · Staff Kuriftu slots"
    )


def _score_prompt() -> str:
    return (
        "📊 <b>Check your gut score</b>\n\n"
        "Text me the Ethiopian foods you ate today and I will calculate your gut health score in seconds.\n\n"
        "<b>Example:</b>\n<code>injera misir ayib</code>\n\n"
        "Or pick a food category below to see what's in each group:"
    )


def _category_foods(category: str) -> str:
    foods = {
        "grains":  "🌾 <b>Grains</b>\ninjera · teff porridge (genfo) · dabo",
        "legumes": "🫘 <b>Legumes</b>\nmisir wot · shiro · kik alicha · ater",
        "meat":    "🍖 <b>Meat</b>\ntibs · kitfo · doro wot",
        "dairy":   "🥛 <b>Dairy</b>\nayib · ergo (yogurt)",
        "veg":     "🥦 <b>Vegetables</b>\ngomen · fasolia",
        "drinks":  "☕ <b>Drinks</b>\nbuna · tej",
    }
    base = foods.get(category, "No foods found in that category.")
    return f"{base}\n\nNow text me the foods you had today — for example:\n<code>injera misir ayib</code>"


HELP_TEXT = (
    "<b>Well-Net Bot Help</b>\n\n"
    "<b>Log a meal:</b> Just type the foods you ate\n"
    "Example: <code>injera misir tej</code>\n\n"
    "<b>Commands:</b>\n"
    "/start — welcome message\n"
    "/menu — show main menu\n"
    "/help — this message\n\n"
    "<b>Keywords that work:</b>\n"
    "TIPS · KURIFTU · EXPERT · FAMILY · SCORE\n\n"
    "<b>Foods I understand:</b>\n"
    "injera · misir · shiro · tibs · kitfo · ayib · ergo · tej · gomen · fasolia · doro · teff · buna · abish"
)
