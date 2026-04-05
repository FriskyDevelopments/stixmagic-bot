from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stixmagic.settings import get_settings
from infra.db import init_db


if __name__ == "__main__":
    settings = get_settings()

    init_db()
    print(
        "Smoke test OK:",
        {



            "db_initialized": True,
            "miniapp_enabled": bool(settings.miniapp_url),
            "bot_mode": settings.bot_mode,
        },
    )