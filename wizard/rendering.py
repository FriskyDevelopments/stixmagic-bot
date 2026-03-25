from __future__ import annotations

from dataclasses import dataclass, field

from wizard.model import WizardEvent


@dataclass(slots=True)
class RenderInstruction:
    """Common UI payload emitted by shared wizard engine."""

    text: str
    buttons: list[list[dict[str, str]]] = field(default_factory=list)
    is_modal: bool = False


class WizardRenderer:
    """Platform adapter boundary for converting wizard events to transport payloads."""

    def render(self, event: WizardEvent) -> RenderInstruction:
        raise NotImplementedError
