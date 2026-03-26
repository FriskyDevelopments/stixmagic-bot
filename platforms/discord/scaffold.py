from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from core.contracts import StixCoreContract
from core.types import PackGenerationInput, ReactionRenderInput


@dataclass(slots=True)
class DiscordContext:
    """Guild/channel/user metadata required by shared flows."""

    guild_id: str | None = None
    channel_id: str | None = None
    user_id: str | None = None
    locale: str | None = None


@dataclass(slots=True)
class DiscordAttachment:
    """Transport-level attachment metadata from Discord interactions."""

    attachment_id: str
    filename: str
    content_type: str | None
    size: int | None
    url: str | None
    media_type: str


@dataclass(slots=True)
class DiscordInteractionEnvelope:
    """Normalized interaction payload used by adapter handlers."""

    interaction_type: int
    command_name: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    component_custom_id: str | None = None
    modal_custom_id: str | None = None
    modal_values: dict[str, str] = field(default_factory=dict)
    attachments: list[DiscordAttachment] = field(default_factory=list)
    context: DiscordContext = field(default_factory=DiscordContext)
    raw_payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DiscordResponse:
    """Discord-native response envelope ready for interaction callback transport."""

    content: str
    ephemeral: bool = False
    attachments: list[dict[str, Any]] = field(default_factory=list)

    def to_interaction_callback(self) -> dict[str, Any]:
        data: dict[str, Any] = {"content": self.content}
        if self.ephemeral:
            # Discord interaction callback flag for ephemeral responses.
            data["flags"] = 64
        if self.attachments:
            data["attachments"] = self.attachments
        return {"type": 4, "data": data}


class DiscordStixAdapter:
    """Discord scaffold that delegates business logic to the shared STIX core engine."""

    def __init__(self, core_engine: StixCoreContract):
        self.core_engine = core_engine

    def parse_interaction_payload(self, payload: Mapping[str, Any]) -> DiscordInteractionEnvelope:
        """Extract slash/component/modal details into a shared adapter envelope."""
        data = payload.get("data") or {}
        member = payload.get("member") or {}
        user = payload.get("user") or member.get("user") or {}

        attachments = [
            self._normalize_attachment(attachment_id, attachment)
            for attachment_id, attachment in (data.get("resolved", {}).get("attachments", {}) or {}).items()
        ]

        modal_values: dict[str, str] = {}
        for component in data.get("components", []) or []:
            for child in component.get("components", []) or []:
                custom_id = child.get("custom_id")
                if custom_id:
                    modal_values[custom_id] = str(child.get("value") or "")

        options = {
            option.get("name"): option.get("value")
            for option in data.get("options", []) or []
            if option.get("name")
        }

        return DiscordInteractionEnvelope(
            interaction_type=int(payload.get("type", 0)),
            command_name=data.get("name"),
            options=options,
            component_custom_id=data.get("custom_id") if payload.get("type") == 3 else None,
            modal_custom_id=data.get("custom_id") if payload.get("type") == 5 else None,
            modal_values=modal_values,
            attachments=attachments,
            context=DiscordContext(
                guild_id=payload.get("guild_id"),
                channel_id=payload.get("channel_id"),
                user_id=user.get("id"),
                locale=payload.get("locale"),
            ),
            raw_payload=payload,
        )

    async def generate_pack(self, file_bytes, media_type: str):
        return await self.core_engine.generate_pack(
            PackGenerationInput(file_bytes=file_bytes, media_type=media_type)
        )

    def generate_reactions(
        self,
        *,
        title: str,
        name: str,
        description: str = "",
        likes: int = 0,
        dislikes: int = 0,
        views: int = 0,
        user_reaction: str | None = None,
    ) -> str:
        payload = ReactionRenderInput(
            title=title,
            name=name,
            description=description,
            likes=likes,
            dislikes=dislikes,
            views=views,
            user_reaction=user_reaction,
        )
        return self.core_engine.generate_reactions(payload).text

    def render_response(self, content: str, *, ephemeral: bool = False) -> DiscordResponse:
        """Render basic Discord interaction callback payloads."""
        return DiscordResponse(content=content, ephemeral=ephemeral)

    async def handle_interaction(
        self,
        payload: Mapping[str, Any],
        fetch_attachment_bytes: Callable[[DiscordAttachment], Any] | None = None,
    ) -> DiscordResponse:
        """Route interaction types and leave transport wiring to the eventual Discord runtime."""
        envelope = self.parse_interaction_payload(payload)

        if envelope.interaction_type == 2 and envelope.command_name == "generate":
            return await self._handle_generate_command(envelope, fetch_attachment_bytes)
        if envelope.interaction_type == 3:
            return self._handle_button_interaction(envelope)
        if envelope.interaction_type == 5:
            return self._handle_modal_submit(envelope)

        return self.render_response(
            "Discord scaffold received an unsupported interaction type.", ephemeral=True
        )

    async def handle_trigger_event(self, event_name: str, context: DiscordContext) -> None:
        """Future hook for shared trigger engine integration."""
        raise NotImplementedError(
            f"Trigger hook '{event_name}' for guild '{context.guild_id}' is not wired yet."
        )

    async def _handle_generate_command(
        self,
        envelope: DiscordInteractionEnvelope,
        fetch_attachment_bytes: Callable[[DiscordAttachment], Any] | None,
    ) -> DiscordResponse:
        if not envelope.attachments:
            return self.render_response(
                "Attach an image or video to use /generate.", ephemeral=True
            )
        if fetch_attachment_bytes is None:
            return self.render_response(
                "Attachment download is not configured in this scaffold yet.", ephemeral=True
            )

        attachment = envelope.attachments[0]
        file_bytes = await fetch_attachment_bytes(attachment)
        result = await self.generate_pack(file_bytes=file_bytes, media_type=attachment.media_type)
        if result is None:
            return self.render_response("Generation failed.", ephemeral=True)

        return DiscordResponse(
            content=f"Generated {result.sticker_format} sticker from {attachment.filename}.",
            ephemeral=True,
            attachments=[
                {
                    "id": 0,
                    "filename": f"stix.{ 'webm' if result.sticker_format == 'video' else 'webp' }",
                    "description": "Generated by STIX core",
                }
            ],
        )

    def _handle_button_interaction(self, envelope: DiscordInteractionEnvelope) -> DiscordResponse:
        return self.render_response(
            f"Button scaffold acknowledged: {envelope.component_custom_id or 'unknown'}",
            ephemeral=True,
        )

    def _handle_modal_submit(self, envelope: DiscordInteractionEnvelope) -> DiscordResponse:
        field_count = len(envelope.modal_values)
        return self.render_response(
            f"Modal scaffold acknowledged ({field_count} fields).", ephemeral=True
        )

    @staticmethod
    def _normalize_attachment(attachment_id: str, raw: Mapping[str, Any]) -> DiscordAttachment:
        content_type = raw.get("content_type")
        media_type = "video" if isinstance(content_type, str) and content_type.startswith("video/") else "image"
        return DiscordAttachment(
            attachment_id=attachment_id,
            filename=str(raw.get("filename") or attachment_id),
            content_type=content_type if isinstance(content_type, str) else None,
            size=int(raw["size"]) if raw.get("size") is not None else None,
            url=raw.get("url") if isinstance(raw.get("url"), str) else None,
            media_type=media_type,
        )
