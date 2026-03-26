from __future__ import annotations


def describe_animation_stack() -> dict[str, tuple[str, ...]]:
    """Describe the animation-owned subsystems without mixing them into plugin space."""
    return {
        "pipeline_modules": (
            "pipeline.asset_model",
            "pipeline.metadata",
            "pipeline.motion_presets",
            "pipeline.exporters",
            "pipeline.packager",
        ),
        "owned_concerns": (
            "motion presets",
            "sphere/animation asset processing",
            "multi-format render exports",
        ),
    }
