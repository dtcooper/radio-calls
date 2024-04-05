from pathlib import Path

import environ


env = environ.Env()


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEV_MODE", False)
DOMAIN_NAME = env("DOMAIN_NAME")

TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_SIP_DOMAIN = env("TWILIO_SIP_DOMAIN")
TWILIO_SIP_HOST_USERNAME = env("TWILIO_SIP_HOST_USERNAME")
TWILIO_TWIML_APP_SID = env("TWILIO_TWIML_APP_SID")
TWILIO_API_KEY = env("TWILIO_API_KEY")
TWILIO_API_SECRET = env("TWILIO_API_SECRET")

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")

GEOIP2_LITE_CITY_DB_PATH = env("GEOIP2_LITE_CITY_DB_PATH")

ALLOWED_HOSTS = [DOMAIN_NAME]
if DEBUG:
    ALLOWED_HOSTS.append("localhost")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

AUTH_USER_MODEL = "api.User"

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third Party
    "admin_extra_buttons",
    "django_countries",
    "django_jsonform",
    "durationwidget",
]
if DEBUG:
    INSTALLED_APPS.append("django_extensions")
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
        # "calls": {  # TODO: local logs?
        #     "handlers": ["console"],
        #     "level": "INFO",
        # },
    },
}

LANGUAGE_CODE = "en-us"

TIME_ZONE = env("TZ", default="US/Eastern")

USE_I18N = True

USE_TZ = True

STATIC_URL = "backend-static/"
STATIC_ROOT = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SHELL_PLUS_IMPORTS = [
    "from api.utils import get_mturk_client, get_mturk_available_balance, get_ip_addr, get_location_from_ip_addr",
]
