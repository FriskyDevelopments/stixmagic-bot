"""Shared runtime contracts and helpers for the Stix Magic product backend."""

from .contracts import (  # noqa: F401
    API_VERSION,
    MINIAPP_AUTH_HEADER,
    PACK_TYPE_ANIMATED,
    PACK_TYPE_IMAGE,
    PACK_TYPE_VIDEO,
    PACK_TYPES,
    PRODUCT_NAME,
)
from .settings import AppSettings, get_settings  # noqa: F401
from .telegram_auth import (  # noqa: F401
    TelegramInitDataError,
    validate_init_data,
)
