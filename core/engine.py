"""Platform-agnostic shared STIX MΛGIC core engine."""

from __future__ import annotations

from dataclasses import replace

from .capabilities import PlatformCapabilities
from .contracts import MediaNormalizer, PackFormatter
from .types import (
    PackGenerationRequest,
    PackGenerationResult,
    PackItemResult,
    ReactionGenerationInput,
    ReactionGenerationOutput,
    ReactionOption,
    ReactionRenderInput,
    ReactionRenderResult,
)


class StixCoreEngine:
    """Shared business-logic engine used by all platform adapters."""

    def __init__(
        self,
        *,
        media_normalizer: MediaNormalizer,
        pack_formatter: PackFormatter | None = None,
    ) -> None:
        self._media_normalizer = media_normalizer
        self._pack_formatter = pack_formatter

    def normalize_generation_request(self, request: PackGenerationRequest) -> PackGenerationRequest:
        """Normalize core pack requests to keep adapter logic thin."""

        raw_title = (request.title or "").strip()
        normalized_title = (raw_title or "My Pack")[:64]
        normalized_inputs = [
            replace(
                item,
                prefer_format=item.prefer_format or ("webm" if item.is_animated_source else "webp"),
                emoji=item.emoji or ["✨"],
            )
            for item in request.sticker_inputs
        ]
        return replace(request, title=normalized_title, sticker_inputs=normalized_inputs)

    async def generate_pack(
        self,
        request: PackGenerationRequest,
        *,
        capabilities: PlatformCapabilities,
    ) -> PackGenerationResult:
        """Generate a normalized pack using shared sticker logic."""

        request = self.normalize_generation_request(request)
        items: list[PackItemResult] = []

        for index, sticker_input in enumerate(request.sticker_inputs):
            try:
                sticker = await self._media_normalizer.normalize_sticker(
                    sticker_input,
                    capabilities=capabilities,
                )
                items.append(PackItemResult(index=index, success=True, sticker=sticker))
            except (ValueError, IOError, OSError) as exc:
                items.append(PackItemResult(index=index, success=False, error=str(exc)))
            except Exception as exc:
                import logging
                logging.exception(f"Unexpected error processing sticker at index {index}")
                raise

        result = PackGenerationResult(
            pack_id=request.pack_id,
            title=request.title,
            items=items,
            warnings=[] if all(item.success for item in items) else ["Some stickers failed to generate."],
            metadata={
                "requested_platform": request.requested_platform,
                "supports_native_sticker_packs": capabilities.supports_native_sticker_packs,
            },
        )
        return await self._format_pack_result(result, capabilities=capabilities)

    async def generate_reactions(
        self,
        request: ReactionGenerationInput,
        *,
        capabilities: PlatformCapabilities,
    ) -> ReactionGenerationOutput:
        """Generate normalized reaction options from a shared heuristic."""

        normalized_prompt = request.prompt.strip().lower()
        if not normalized_prompt:
            return ReactionGenerationOutput(options=[])

        base_options = [
            ReactionOption(key="spark", label="✨ Spark", score=0.66),
            ReactionOption(key="hype", label="🔥 Hype", score=0.61),
            ReactionOption(key="approve", label="✅ Approve", score=0.58),
        ]
        if "sad" in normalized_prompt or "oops" in normalized_prompt:
            base_options.insert(0, ReactionOption(key="comfort", label="💜 Comfort", score=0.72))
        if not capabilities.supports_reactions:
            base_options = [ReactionOption(key="text", label="Send text reaction", score=0.5)]

        return ReactionGenerationOutput(options=base_options[: max(1, request.max_results)])

    async def _format_pack_result(
        self,
        result: PackGenerationResult,
        *,
        capabilities: PlatformCapabilities,
    ) -> PackGenerationResult:
        if not self._pack_formatter:
            return result
        return await self._pack_formatter.format_pack_result(result, capabilities=capabilities)

    async def format_pack_reactions(
        self,
        payload: ReactionRenderInput,
    ) -> ReactionRenderResult:
        """Render a normalized reaction + metadata text block for platform adapters."""
        import html

        like_mark = " ◀" if payload.user_reaction == "like" else ""
        dislike_mark = " ◀" if payload.user_reaction == "dislike" else ""

        text = (
            f"🔍 <b>{html.escape(payload.title)}</b>\n"
            f"<code>{html.escape(payload.name)}</code>\n"
        )
        if payload.description:
            text += f"\n<i>{html.escape(payload.description)}</i>\n"
        text += (
            f"\n👁 {payload.views}  ·  "
            f"👍 {payload.likes}{like_mark}  ·  "
            f"👎 {payload.dislikes}{dislike_mark}"
        )

        return ReactionRenderResult(text=text)