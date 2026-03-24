"""TTL cleanup worker for creator drafts.

Usage:
    python scripts/creator_cleanup_worker.py
"""

from infra.db import cleanup_expired_creator_drafts


def main() -> None:
    deleted = cleanup_expired_creator_drafts()
    print(f"creator_cleanup_deleted={deleted}")


if __name__ == "__main__":
    main()
