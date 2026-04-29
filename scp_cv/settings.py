"""Django settings for the SCP-cv single-host playback platform."""

from __future__ import annotations

from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_LANGUAGE_CODE=(str, "zh-hans"),
    DJANGO_TIME_ZONE=(str, "Asia/Shanghai"),
    GRPC_PORT=(int, 50051),
    MEDIAMTX_SRT_PORT=(int, 8890),
    MEDIAMTX_RTSP_PORT=(int, 8554),
    MEDIAMTX_SRT_READ_HOST=(str, ""),
)
environ.Env.read_env(BASE_DIR / ".env")


SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-change-me-for-development-only",
)
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = [
    host.strip()
    for host in env("DJANGO_ALLOWED_HOSTS", default="127.0.0.1,localhost").split(",")
    if host.strip()
]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_socio_grpc",
    "scp_cv.apps.dashboard.apps.DashboardConfig",
    "scp_cv.apps.playback.apps.PlaybackConfig",
    "scp_cv.apps.streams.apps.StreamsConfig",
]

MIDDLEWARE = [
    "scp_cv.cors_middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "scp_cv.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "scp_cv.context_processors.runtime_context",
            ],
        },
    },
]

WSGI_APPLICATION = "scp_cv.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = env("DJANGO_LANGUAGE_CODE")
TIME_ZONE = env("DJANGO_TIME_ZONE")
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


GRPC_HOST = env("GRPC_HOST", default="127.0.0.1")
GRPC_PORT = env.int("GRPC_PORT")
MEDIAMTX_BIN_PATH = env("MEDIAMTX_BIN_PATH", default="")
MEDIAMTX_API_BASE = env("MEDIAMTX_API_BASE", default="http://127.0.0.1:9997")
MEDIAMTX_SRT_PORT = env.int("MEDIAMTX_SRT_PORT")
MEDIAMTX_RTSP_PORT = env.int("MEDIAMTX_RTSP_PORT")
MEDIAMTX_SRT_PUBLIC_HOST = env("MEDIAMTX_SRT_PUBLIC_HOST", default="")
MEDIAMTX_SRT_READ_HOST = env("MEDIAMTX_SRT_READ_HOST", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "scp-cv.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django.server": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

GRPC_FRAMEWORK = {
    "ROOT_HANDLERS_HOOK": "scp_cv.grpc_handlers.grpc_handlers",
    "GRPC_ASYNC": True,
    "SERVER_OPTIONS": [
        ("grpc.max_send_message_length", 100 * 1024 * 1024),
        ("grpc.max_receive_message_length", 100 * 1024 * 1024),
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}
