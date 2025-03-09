from pathlib import Path

import environ

from api import constants as api_constants


env = environ.Env()
env.read_env("/.env")


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
DOMAIN_NAME = env("DOMAIN_NAME")
GIT_REV = env("GIT_REV", default="unknown")
BUILD_TIME = env("BUILD_TIME", default="2000-01-01T00:00:00Z")

TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_OUTGOING_NUMBER = env("TWILIO_OUTGOING_NUMBER")
TWILIO_FORWARD_NUMBERS = env.list("TWILIO_FORWARD_NUMBERS")
TWILIO_SIP_DOMAIN = env("TWILIO_SIP_DOMAIN")
TWILIO_SIP_HOST_USERNAME = env("TWILIO_SIP_HOST_USERNAME", default="host")
TWILIO_SIP_PICKUP_USERNAME = env("TWILIO_SIP_PICKUP_USERNAME", default="pickup")
TWILIO_SIP_SIMULATE_USERNAME = env("TWILIO_SIP_SIMULATE_USERNAME", default="simulate")
TWILIO_TWIML_APP_SID = env("TWILIO_TWIML_APP_SID")
TWILIO_API_KEY = env("TWILIO_API_KEY")
TWILIO_API_SECRET = env("TWILIO_API_SECRET")

ALLOW_MTURK_PRODUCTION_ACCESS = env.bool("ALLOW_MTURK_PRODUCTION_ACCESS", default=False)
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")

GEOIP2_LITE_CITY_DB_PATH = env("GEOIP2_LITE_CITY_DB_PATH")

ALLOWED_HOSTS = [DOMAIN_NAME]
if DEBUG:
    ALLOWED_HOSTS.append("localhost")
    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda req: req.user.is_superuser}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

AUTH_USER_MODEL = "api.User"

INSTALLED_APPS = [
    "admin_notice",  # Needs to come before django.contrib.admin
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third Party
    "admin_extra_buttons",
    "constance",
    "django_countries",
    "django_jsonform",
    "durationwidget",
    "phonenumber_field",
]
if DEBUG:
    INSTALLED_APPS.extend([
        "debug_toolbar",
        "django_extensions",
    ])
INSTALLED_APPS.extend([
    # Local
    "api",
])

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "api.middleware.SendTwilioUserDefinedMessageAtEndOfRequestMiddleware",
]
if DEBUG:
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

ROOT_URLCONF = "calls.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "api" / "templates"],  # To make base_site.html work
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "admin_notice.context_processors.notice",
                "api.context_processors.global_template_vars",
            ],
        },
    },
]

WSGI_APPLICATION = "calls.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "db",
        "PORT": 5432,
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        }
    },
    "formatters": {
        "console": {
            "format": "[%(asctime)s] %(levelname)s:%(name)s:%(lineno)s:%(funcName)s: %(message)s",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "console", "level": "INFO"},
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "huey": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "calls": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

LANGUAGE_CODE = "en-us"

TIME_ZONE = env("TZ", default="US/Eastern")

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = "/serve/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = "/serve/media/"

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = 315360000  # 10 years

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ADMIN_NOTICE_TEXT = "Development Environment" if DEBUG else "WARNING: Production Environment"
ADMIN_NOTICE_TEXT_COLOR = "#000000" if DEBUG else "#ffffff"
ADMIN_NOTICE_BACKGROUND = "#73e33c" if DEBUG else "#ff0000"

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"
CONSTANCE_ADDITIONAL_FIELDS = {
    "phone_mode": [
        "django.forms.fields.ChoiceField",
        {
            "widget": "django.forms.Select",
            "choices": api_constants.PHONE_MODES,
        },
    ],
}

CONSTANCE_CONFIG = {
    "PHONE_MODE": (api_constants.PHONE_MODE_TAKING_CALLS, "Phone's mode of operation", "phone_mode"),
    "ANSWERING_MACHINE_DETECTION": (
        True,
        (
            "Enable answering machine detection code for outgoing consent-flow calls. Disable during development"
            " because they can get expensive."
        ),
    ),
}

if DEBUG:
    CONSTANCE_CONFIG.update({
        "SKIP_TWILIO_PLAY": (False, "[DEBUG only] Skip Twilio <Play /> verb, just use <Say /> verb instead)"),
    })

SHELL_PLUS_IMPORTS = [
    (
        "from api.utils import get_mturk_client, get_ip_addr, get_location_from_ip_addr, block_or_unblock_worker,"
        " block_or_unblock_workers"
    ),
]
