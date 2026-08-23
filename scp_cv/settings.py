"""Django settings for the SCP-cv single-host playback platform."""

from __future__ import annotations

from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
APP_LOG_DIR = LOG_DIR / "app"
APP_LOG_DIR.mkdir(parents=True, exist_ok=True)
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_LANGUAGE_CODE=(str, "zh-hans"),
    DJANGO_TIME_ZONE=(str, "Asia/Shanghai"),
    GRPC_PORT=(int, 50051),
    MEDIAMTX_SRT_PORT=(int, 8890),
    MEDIAMTX_RTSP_PORT=(int, 8554),
    MEDIAMTX_SRT_READ_HOST=(str, ""),
    MEDIAMTX_SRT_READ_LATENCY_MS=(int, 50),
    MEDIAMTX_SRT_PUBLISH_LATENCY_US=(int, 30000),
    MEDIAMTX_RTSP_READ_TRANSPORT=(str, "tcp"),
    STREAM_VLC_NETWORK_CACHING_MS=(int, 50),
    STREAM_VLC_LIVE_CACHING_MS=(int, 50),
    STREAM_VLC_FILE_CACHING_MS=(int, 0),
    STREAM_VLC_CLOCK_JITTER=(int, 0),
    STREAM_VLC_CLOCK_SYNCHRO=(int, 0),
    STREAM_VLC_DROP_LATE_FRAMES=(bool, True),
    STREAM_VLC_SKIP_FRAMES=(bool, True),
    STREAM_PREHEAT_NETWORK_CACHING_MS=(int, 100),
    STREAM_PREHEAT_LIVE_CACHING_MS=(int, 100),
    STREAM_PREHEAT_TTL_SECONDS=(float, 60.0),
)
environ.Env.read_env(BASE_DIR / ".env")


SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-change-me-for-development-only",
)
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = [
    host.strip()
    for host in env("DJANGO_ALLOWED_HOSTS", default="*").split(",")
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
    "scp_cv.auth_middleware.ApiAuthMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# CORS 白名单：允许 Vite dev server / 本机调试控制台直连后端；带 cookie 的请求
# 浏览器层禁止 Allow-Origin=*，因此必须显式枚举可信源。
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in env(
        "DJANGO_CORS_ALLOWED_ORIGINS",
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
    ).split(",")
    if origin.strip()
]

# Django 4+ 必须显式声明 CSRF 可信源（schema://host:port），否则 POST 会被
# CsrfViewMiddleware 直接拒绝；与 CORS_ALLOWED_ORIGINS 同源对齐即可。
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in env(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
    ).split(",")
    if origin.strip()
]

# 单机部署默认 Lax 足够；跨端口同站点 cookie 可正常携带。
SESSION_COOKIE_SAMESITE = env("DJANGO_SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = env("DJANGO_CSRF_COOKIE_SAMESITE", default="Lax")
# CSRF cookie 不能设为 HttpOnly，前端要把 csrftoken 读出来回填到请求头。
CSRF_COOKIE_HTTPONLY = False

LOGIN_URL = "/api/auth/login/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

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
_configured_local_media_roots = env.list("LOCAL_MEDIA_ALLOWED_ROOTS", default=[])
LOCAL_MEDIA_ALLOWED_ROOTS = [
    Path(configured_root).expanduser().resolve()
    for configured_root in _configured_local_media_roots
    if str(configured_root).strip()
] or [MEDIA_ROOT.resolve()]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


GRPC_HOST = env("GRPC_HOST", default="127.0.0.1")
GRPC_PORT = env.int("GRPC_PORT")
MEDIAMTX_BIN_PATH = env("MEDIAMTX_BIN_PATH", default="")
MEDIAMTX_API_BASE = env("MEDIAMTX_API_BASE", default="http://127.0.0.1:9997")
MEDIAMTX_SRT_PORT = env.int("MEDIAMTX_SRT_PORT")
MEDIAMTX_RTSP_PORT = env.int("MEDIAMTX_RTSP_PORT")
MEDIAMTX_SRT_PUBLIC_HOST = env("MEDIAMTX_SRT_PUBLIC_HOST", default="")
MEDIAMTX_SRT_READ_HOST = env("MEDIAMTX_SRT_READ_HOST", default="")
MEDIAMTX_SRT_READ_LATENCY_MS = env.int("MEDIAMTX_SRT_READ_LATENCY_MS")
MEDIAMTX_SRT_PUBLISH_LATENCY_US = env.int("MEDIAMTX_SRT_PUBLISH_LATENCY_US")
MEDIAMTX_RTSP_READ_TRANSPORT = env("MEDIAMTX_RTSP_READ_TRANSPORT")
STREAM_VLC_NETWORK_CACHING_MS = env.int("STREAM_VLC_NETWORK_CACHING_MS")
STREAM_VLC_LIVE_CACHING_MS = env.int("STREAM_VLC_LIVE_CACHING_MS")
STREAM_VLC_FILE_CACHING_MS = env.int("STREAM_VLC_FILE_CACHING_MS")
STREAM_VLC_CLOCK_JITTER = env.int("STREAM_VLC_CLOCK_JITTER")
STREAM_VLC_CLOCK_SYNCHRO = env.int("STREAM_VLC_CLOCK_SYNCHRO")
STREAM_VLC_DROP_LATE_FRAMES = env.bool("STREAM_VLC_DROP_LATE_FRAMES")
STREAM_VLC_SKIP_FRAMES = env.bool("STREAM_VLC_SKIP_FRAMES")
STREAM_PREHEAT_NETWORK_CACHING_MS = env.int("STREAM_PREHEAT_NETWORK_CACHING_MS")
STREAM_PREHEAT_LIVE_CACHING_MS = env.int("STREAM_PREHEAT_LIVE_CACHING_MS")
STREAM_PREHEAT_TTL_SECONDS = env.float("STREAM_PREHEAT_TTL_SECONDS")
LIBREOFFICE_BIN_PATH = env("LIBREOFFICE_BIN_PATH", default="")
LIBREOFFICE_CONNECT_TIMEOUT_SECONDS = env.float(
    "LIBREOFFICE_CONNECT_TIMEOUT_SECONDS",
    default=10.0,
)
LIBREOFFICE_BRIDGE_COMMAND_TIMEOUT_SECONDS = env.float(
    "LIBREOFFICE_BRIDGE_COMMAND_TIMEOUT_SECONDS",
    default=120.0,
)
PPT_PREVIEW_WORKER_TIMEOUT_SECONDS = env.float(
    "PPT_PREVIEW_WORKER_TIMEOUT_SECONDS",
    default=180.0,
)
PPT_PLAYBACK_EXPORT_TIMEOUT_SECONDS = env.float(
    "PPT_PLAYBACK_EXPORT_TIMEOUT_SECONDS",
    default=180.0,
)
# 新上传演示文稿是否自动检测静态内容并导出 PDF；关闭后统一走 PowerPoint 模式。
SLIDES_PDF_AUTO_CONVERT = env.bool("SLIDES_PDF_AUTO_CONVERT", default=True)

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
            "filename": APP_LOG_DIR / "scp-cv.log",
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

def _grpc_server_interceptors() -> list:
    """
    返回 gRPC 服务端拦截器实例列表。
    socio-grpc 不把 SERVER_INTERCEPTORS 加入 IMPORT_STRINGS，必须传具体实例；
    使用工厂函数延迟到 import 完成后再实例化，避免 settings 加载阶段的循环依赖。
    :return: List[grpc.aio.ServerInterceptor]
    """
    from scp_cv.grpc_auth import GrpcAuthInterceptor

    return [GrpcAuthInterceptor()]


GRPC_FRAMEWORK = {
    "ROOT_HANDLERS_HOOK": "scp_cv.grpc_handlers.grpc_handlers",
    "GRPC_ASYNC": True,
    "SERVER_OPTIONS": [
        ("grpc.max_send_message_length", 100 * 1024 * 1024),
        ("grpc.max_receive_message_length", 100 * 1024 * 1024),
    ],
    # gRPC 与 REST 共用 Django session：每个 RPC 必须携带有效 sessionid metadata
    # （或 cookie 头），未登录返回 UNAUTHENTICATED。
    "SERVER_INTERCEPTORS": _grpc_server_interceptors(),
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
