from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal

MediaType = Literal["image", "video", "sticker"]
StickerFormat = Literal["static", "video"]
ReactionType = Literal["like", "dislike"]


@dataclass(slots=True)
class PackGenerationInput:
    file_bytes: io.BytesIO
    media_type: MediaType


@dataclass(slots=True)
class PackGenerationResult:
    sticker_file: io.BytesIO
    sticker_format: StickerFormat


@dataclass(slots=True)
class ReactionRenderInput:
    title: str
    name: str
    description: str = ""
    likes: int = 0
    dislikes: int = 0
    views: int = 0
    user_reaction: ReactionType | None = None


@dataclass(slots=True)
class ReactionRenderResult:
    text: str
