"""Shared DTOs for the STIX MΛGIC core engine.

These types are intentionally platform-agnostic so both Telegram and Discord
adapters can use the same contracts without duplicating business logic.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(slots=True)
class PlatformEventContext:
    """Event envelope passed from adapters into the core engine.

    Notes:
        - ``chat_id`` is kept for backwards compatibility / Telegram semantics.
        - ``conversation_id`` is the preferred, platform-agnostic identifier.
    """

    platform: str
    event_id: str | None
    user_id: str | int
    chat_id: str | int | None = None
    conversation_id: str | int | None = None
    message_id: str | int | None = None
    command: str | None = None
    raw_event: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Keep ``chat_id`` and ``conversation_id`` in sync for callers that
        # may use either name depending on the adapter (Telegram, Discord, ...).
        if self.conversation_id is None and self.chat_id is not None:
            self.conversation_id = self.chat_id
        elif self.conversation_id is not None and self.chat_id is None:
            self.chat_id = self.conversation_id


@dataclass(slots=True)
class UserSessionContext:
    """Normalized identity and session data shared across flows."""

    user_id: str | int
    session_id: str
    locale: str | None = None
    username: str | None = None
    display_name: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StickerGenerationInput:
    """Request DTO for single sticker generation/normalization."""

    source_bytes: bytes
    source_mime_type: str
    source_name: str | None = None
    emoji: list[str] = field(default_factory=lambda: ["✨"])
    is_animated_source: bool = False
    prefer_format: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StickerGenerationOutput:
    """Result DTO for generated/normalized sticker media."""

    sticker_bytes: bytes
    sticker_format: str
    width: int | None = None
    height: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReactionGenerationInput:
    """Request DTO for reaction generation."""

    prompt: str
    intensity: float = 0.5
    style: str | None = None
    max_results: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReactionOption:
    """A single reaction candidate emitted by the core engine."""

    key: str
    label: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReactionGenerationOutput:
    """Result DTO for reaction generation."""

    options: list[ReactionOption]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PackGenerationRequest:
    """Request DTO for pack generation/formatting."""

    pack_id: str
    title: str
    sticker_inputs: list[StickerGenerationInput]
    owner_user_id: str | int | None = None
    requested_platform: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PackItemResult:
    """Item-level result for generated pack entries."""

    index: int
    success: bool
    sticker: StickerGenerationOutput | None = None
    error: str | None = None


@dataclass(slots=True)
class PackGenerationResult:
    """Result DTO for pack generation/formatting."""

    pack_id: str
    title: str
    items: list[PackItemResult]
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Legacy DTOs — kept for backward compatibility with existing adapters that
# pre-date the richer core type system.  New code should use the types above.
# ---------------------------------------------------------------------------

MediaType = Literal["image", "video", "sticker"]
StickerFormat = Literal["static", "video"]
ReactionType = Literal["like", "dislike"]


@dataclass(slots=True)
class PackGenerationInput:
    """Legacy request DTO used by the simplified Telegram adapter path."""

    file_bytes: io.BytesIO
    media_type: MediaType


@dataclass(slots=True)
class ReactionRenderInput:
    """Legacy request DTO for catalog/reaction text rendering."""

    title: str
    name: str
    description: str = ""
    likes: int = 0
    dislikes: int = 0
    views: int = 0
    user_reaction: ReactionType | None = None


@dataclass(slots=True)
class ReactionRenderResult:
    """Legacy result DTO for catalog/reaction text rendering."""

    text: str
