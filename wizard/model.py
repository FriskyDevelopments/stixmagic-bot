from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


ValidationFn = Callable[[Any, dict[str, Any]], tuple[bool, str | None]]
TransitionFn = Callable[[Any, dict[str, Any]], str | None]


@dataclass(slots=True)
class WizardTransition:
    """Defines how to move from the current step to the next step."""

    next_step: str | None = None
    resolver: TransitionFn | None = None


@dataclass(slots=True)
class WizardStep:
    """One platform-agnostic wizard step."""

    id: str
    prompt: str
    value_key: str | None = None
    validation: ValidationFn | None = None
    transition: WizardTransition = field(default_factory=WizardTransition)
    side_effects: list[str] = field(default_factory=list)
    completion_message: str | None = None


@dataclass(slots=True)
class WizardDefinition:
    """Wizard definition that can be rendered on any chat platform."""

    id: str
    start_step: str
    steps: dict[str, WizardStep]


@dataclass(slots=True)
class WizardSession:
    """Mutable execution state for one in-progress wizard."""

    wizard_id: str
    current_step_id: str
    values: dict[str, Any] = field(default_factory=dict)
    completed: bool = False


@dataclass(slots=True)
class WizardEvent:
    """Engine output consumed by platform adapters for rendering."""

    prompt: str
    step_id: str
    completed: bool
    completion_message: str | None = None
    validation_error: str | None = None
    side_effects: list[str] = field(default_factory=list)