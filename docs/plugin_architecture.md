# Plugin Architecture

## Core bot ownership

The main Stix Magic bot owns the shared runtime and sticker/animation system:

- Telegram conversation orchestration and menus
- sticker processing flows and mask timing flows
- sphere, motion preset, and animation/export pipeline logic
- shared catalog and database functionality that applies to all operators

These concerns live under the `src/bot`, `src/stickers`, `src/animations`, `src/core`, and `src/config` boundaries.

## Truck Club ownership

The Truck Club is now documented as a separate plugin layer under `src/plugins/truck_club`.
It owns:

- Truck Club-specific commands
- Truck Club-specific event hooks
- Truck Club-specific metrics names and configuration namespace
- any future Truck Club rules that should *not* be mixed into general sticker flows

## How to add future plugins

1. Create a folder under `src/plugins/<plugin_slug>`.
2. Keep plugin commands, metrics, and hook descriptions inside that package.
3. Expose only a manifest through the shared `PluginRegistry` in `src/core/plugins.py`.
4. Add plugin-specific environment variables under a dedicated namespace such as `MY_PLUGIN_*`.
5. Update README/docs rather than editing the shared bot layer unless a new generic extension hook is required.

## Boundary rule

If logic only exists for one partner or community, it belongs in a plugin package.
If logic applies to sticker creation, animation processing, timing flows, or shared event handling for every deployment, it belongs in the main bot system.
