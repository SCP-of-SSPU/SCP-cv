from __future__ import annotations

from django.conf import settings


def runtime_context(request: object) -> dict[str, str | bool]:
    """Expose small runtime details to the shared base template."""

    return {
        "project_name": "SCP-cv",
        "runtime_mode": "DEBUG 模式" if settings.DEBUG else "生产模式",
        "grpc_endpoint": f"{settings.GRPC_HOST}:{settings.GRPC_PORT}",
        "media_root_path": str(settings.MEDIA_ROOT),
    }
