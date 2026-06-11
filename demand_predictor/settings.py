"""
Django settings for demand_predictor project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ensure logs directory exists
(BASE_DIR / "logs").mkdir(exist_ok=True)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_apscheduler",
    "states",
    "predictions",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "demand_predictor.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "dashboard" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "demand_predictor.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "dashboard" / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ENABLE_SCHEDULER = os.environ.get("ENABLE_SCHEDULER", "true").lower() == "true"

APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "demand_predictor.log",
            "maxBytes": 5 * 1024 * 1024,  # 5 MB
            "backupCount": 5,
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "apscheduler": {
            "handlers": ["console", "file"],
            "level": "WARNING",  # suppress APScheduler's noisy INFO spam
            "propagate": False,
        },
        "django": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}