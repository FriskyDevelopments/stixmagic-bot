"""Cross-surface product constants for bot and Mini App flows."""

PRODUCT_NAME = "stixmagic-product-backend"
API_VERSION = "1.1"

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