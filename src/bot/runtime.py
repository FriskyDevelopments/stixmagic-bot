from __future__ import annotations

from src.core.runtime import build_runtime


def build_runtime_summary() -> dict[str, object]:
    runtime = build_runtime()
    return {
        "core": [
            {"owner": boundary.owner, "responsibilities": list(boundary.responsibilities)}
            for boundary in runtime.core_boundaries
        ],
        "plugins": [
            {
                "slug": manifest.slug,
                "display_name": manifest.display_name,
                "config_namespace": manifest.config_namespace,
                "commands": [command.name for command in manifest.commands],
            }
            for manifest in runtime.enabled_plugin_manifests()
        ],
    }
