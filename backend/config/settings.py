"""
Well-Net Django Settings
Flat config — single file, env-driven.
"""
import sys
import os
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv
import dj_database_url


# 1. Standard, explicit path tracking relative to config/settings.py
# __file__ = backend/config/settings.py -> parent.parent = backend/
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Force Python to explicitly register the backend root in its search index
# This guarantees that 'config.wsgi' can be resolved regardless of execution context
sys.path.insert(0, str(BASE_DIR))

# 3. Handle Render container path flattening if deployed live
if os.environ.get("RENDER"):
    if os.path.exists("manage.py"):
        BASE_DIR = Path(".").resolve()
        if str(BASE_DIR) not in sys.path:
            sys.path.insert(0, str(BASE_DIR))
# ── Core ──────────────────────────────────────────────────────────────────────
SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-secret-change-in-production")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = list(config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv()))

# Safely append the live production URL so Render can serve the application
if "well-net-backend.onrender.com" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("well-net-backend.onrender.com")

# ── Apps ──────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "django_celery_beat",
    # Well-Net apps (flat)
    "core",
    "users",
    "foods",
    "wellness",
    "ai",
    "experts",
    "packages",
    "notifications",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Placed precisely after SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# ── Database ──────────────────────────────────────────────────────────────────
PRODUCTION_DB_URL = os.environ.get('DATABASE_URL')

if PRODUCTION_DB_URL:
    # We are on Render! Use the production database configuration
    DATABASES = {
        "default": dj_database_url.config(
            default=PRODUCTION_DB_URL,
            conn_max_age=600
        )
    }
else:
    # We are local! Safely read your local .env configuration keys
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="wellnetdb"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# ── JWT ───────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# ── CORS ──────────────────────────────────────────────────────────────────────
# 1. Parse the base array from your environment safely
CORS_ALLOWED_ORIGINS = list(
    config(
        "CORS_ALLOWED_ORIGINS",
        default="http://localhost:3000,http://127.0.0.1:3000",
        cast=Csv(),
    )
)

PRODUCTION_FRONTEND = "https://well-net.vercel.app"
if PRODUCTION_FRONTEND not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(PRODUCTION_FRONTEND)

PRODUCTION_FRONTEND_ALT = "https://well-net-frontend.vercel.app"
if PRODUCTION_FRONTEND_ALT not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(PRODUCTION_FRONTEND_ALT)

CORS_ALLOW_CREDENTIALS = True  # Kept only one instance here

from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    'accept-language',
]


# ── External APIs ─────────────────────────────────────────────────────────────
GROQ_API_KEY = config("GROQ_API_KEY", default="")
AT_API_KEY = config("AT_API_KEY", default="")
AT_USERNAME = config("AT_USERNAME", default="sandbox")
TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN", default="")
KURIFTU_API_KEY = config("KURIFTU_API_KEY", default="")

# ── Celery / Redis ────────────────────────────────────────────────────────────
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = "Africa/Addis_Ababa"
CELERY_BEAT_SCHEDULE = {
    "daily-wellness-reminders": {
        "task": "notifications.tasks.send_daily_wellness_tip",
        "schedule": 60 * 60 * 8,  # 8 AM Addis Ababa time
    },
    "offpeak-deal-notifications": {
        "task": "notifications.tasks.send_offpeak_deals",
        "schedule": 60 * 60 * 2,  # every 2 hours
    },
    "weekly-wellness-report": {
        "task": "notifications.tasks.send_weekly_report",
        "schedule": 60 * 60 * 24 * 7,  # weekly
    },
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Addis_Ababa"
USE_I18N = True
USE_TZ = True

# ── Static / Media ────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Only include the static directory rule if the directory physically exists on disk
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
] if os.path.exists(os.path.join(BASE_DIR, "static")) else []

# Enable WhiteNoise storage compression and cache management for assets
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_KEEP_ONLY_HASHED_FILES = True

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Production Operations & Security ──────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

if os.environ.get("RENDER"):
    # Security adjustments specific to Render's reverse proxy structure
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Force production cookies and tokens to accept cross-origin HTTPS transit safely
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    CSRF_TRUSTED_ORIGINS = [
        'https://well-net-backend.onrender.com',
        'https://well-net.vercel.app',
        'https://well-net-frontend.vercel.app'
    ]