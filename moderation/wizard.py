from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WizardIntent:
    action: str | None
    confidence: float
    duration_seconds: int | None = None
    reason: str | None = None


class WizardInterpreter:
    """Intent resolver for non-command-first moderation UX."""

    SHORTCUTS = {
        "handle this": "warn_user",
        "warn user": "warn_user",
        "ban user": "ban_user",
        "delete this": "delete_message",
        "pin this": "pin_message",
    }

    def parse(self, text: str) -> WizardIntent:
        normalized = (text or "").strip().lower()
        if not normalized:
            return WizardIntent(action=None, confidence=0.0)

        if normalized.startswith("mute"):
            seconds = self._parse_mute_duration(normalized)
            return WizardIntent(action="mute_user", confidence=0.93, duration_seconds=seconds)

        for phrase, action in self.SHORTCUTS.items():
            if phrase in normalized:
                return WizardIntent(action=action, confidence=0.88)

        return WizardIntent(action=None, confidence=0.25)

    @staticmethod
    def _parse_mute_duration(text: str) -> int:
        # Supports patterns like: "mute 10m", "mute 1h", default 10m.
        tokens = text.split()
        if len(tokens) < 2:
            return 600

        token = tokens[1]
        if token.endswith("m") and token[:-1].isdigit():
            return int(token[:-1]) * 60
        if token.endswith("h") and token[:-1].isdigit():
            return int(token[:-1]) * 3600
        if token.isdigit():
            return int(token)
        return 600
