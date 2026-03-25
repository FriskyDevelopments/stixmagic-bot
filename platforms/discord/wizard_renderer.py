from __future__ import annotations

from wizard.model import WizardEvent
from wizard.rendering import RenderInstruction, WizardRenderer


class DiscordWizardRenderer(WizardRenderer):
    """Maps shared wizard events to Discord follow-up/button/modal metadata."""

    def render(self, event: WizardEvent) -> RenderInstruction:
        text = event.prompt
        if event.validation_error:
            text = f"⚠ {event.validation_error}\n\n{event.prompt}"

        buttons = []
        is_modal = False
        if event.step_id == "confirm":
            buttons = [[{"label": "Confirm", "custom_id": "wizard_yes"}, {"label": "Restart", "custom_id": "wizard_no"}]]
        elif event.step_id == "ask_title":
            is_modal = True

        return RenderInstruction(text=text, buttons=buttons, is_modal=is_modal)
