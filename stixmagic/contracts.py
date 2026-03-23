"""Shared product constants and Telegram hand-off contracts."""

PRODUCT_NAME = "STIX MΛGIC"
API_VERSION = "2.0"

MINIAPP_AUTH_HEADER = "X-Telegram-Init-Data"

START_PAYLOAD_CREATE = "create-pack"
START_PAYLOAD_ADD = "add-sticker"
START_PAYLOAD_MANAGE = "manage-packs"
START_PAYLOAD_MAGIC = "magic-cut"
START_PAYLOAD_FEATURE = "feature-pack"

PACK_TYPE_IMAGE = "image"
PACK_TYPE_ANIMATED = "animated"
PACK_TYPE_VIDEO = "video"
PACK_TYPES = {PACK_TYPE_IMAGE, PACK_TYPE_ANIMATED, PACK_TYPE_VIDEO}
