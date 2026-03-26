from __future__ import annotations

from typing import Any

from wizard.model import WizardDefinition, WizardEvent, WizardSession


class WizardEngine:
    """Shared platform-agnostic runtime for wizard definitions."""

    def __init__(self, definition: WizardDefinition):
        self.definition = definition

    def start(self) -> tuple[WizardSession, WizardEvent]:
        if self.definition.start_step not in self.definition.steps:
            available_steps = list(self.definition.steps.keys())
            raise ValueError(
                f"Invalid start_step '{self.definition.start_step}'. "
                f"Available step ids: {available_steps}"
            )
        session = WizardSession(
            wizard_id=self.definition.id,
            current_step_id=self.definition.start_step,
        )
        step = self.definition.steps[session.current_step_id]
        return session, WizardEvent(prompt=step.prompt, step_id=step.id, completed=False)

    def submit(self, session: WizardSession, raw_value: Any) -> WizardEvent:
        if session.wizard_id != self.definition.id:
            raise ValueError("Session does not belong to this wizard engine.")
        if session.completed:
            raise ValueError("Cannot submit to a completed wizard session.")

        step = self.definition.steps[session.current_step_id]

        if step.validation:
            ok, error = step.validation(raw_value, session.values)
            if not ok:
                return WizardEvent(
                    prompt=step.prompt,
                    step_id=step.id,
                    completed=False,
                    validation_error=error,
                )

        if step.value_key:
            session.values[step.value_key] = raw_value

        next_step = None
        if step.transition.resolver:
            next_step = step.transition.resolver(raw_value, session.values)
        elif step.transition.next_step:
            next_step = step.transition.next_step

        if not next_step:
            session.completed = True
            return WizardEvent(
                prompt=step.prompt,
                step_id=step.id,
                completed=True,
                completion_message=step.completion_message,
                side_effects=step.side_effects.copy() if step.side_effects else [],
            )

        if next_step not in self.definition.steps:
            raise KeyError(f"Transition resolver returned unknown step id: {next_step}")

        session.current_step_id = next_step
        upcoming = self.definition.steps[next_step]
        return WizardEvent(
            prompt=upcoming.prompt,
            step_id=upcoming.id,
            completed=False,
            side_effects=[],
        )