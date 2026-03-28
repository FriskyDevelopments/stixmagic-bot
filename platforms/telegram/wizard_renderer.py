from __future__ import annotations

from wizard.model import WizardEvent
from wizard.rendering import RenderInstruction, WizardRenderer


class TelegramWizardRenderer(WizardRenderer):
    """Maps shared wizard events to Telegram-friendly prompt + inline keyboard metadata."""

    def render(self, event: WizardEvent) -> RenderInstruction:
        if event.completed:
            text = event.completion_message or event.prompt
            return RenderInstruction(text=text, buttons=[])

        text = event.prompt
        if event.validation_error:
            text = f"⚠ {event.validation_error}\n\n{event.prompt}"

        buttons = []
        if event.step_id == "confirm":
            buttons = [
                [
                    {"label": "✅ Confirm", "callback_data": "menu_wizard_confirm"},
                    {"label": "↩ Restart", "callback_data": "menu_wizard_restart"},
                ]
            ]

        return RenderInstruction(text=text, buttons=buttons)