# MagicStix Architecture

## Overview

MagicStix is a **visual asset ecosystem** built on top of the StixMagic Telegram bot.
The bot serves as the asset-creation engine; a multi-layer pipeline transforms those
base assets into distributable products across multiple formats and platforms.

---

## Five-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 – BOT LAYER                                            │
│  Telegram bot (main.py)                                         │
│  Generates clean transparent base assets (PNG/WebP) from user   │
│  input; stores them in assets/source/ by category.              │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ base assets
┌─────────────────────────────────▼───────────────────────────────┐
│  LAYER 2 – ASSET & METADATA LAYER                               │
│  pipeline/asset_model/   – Asset dataclass + category/theme     │
│  pipeline/metadata/      – AssetCatalog (JSON persistence)      │
│  assets/catalog.json     – On-disk index of all known assets    │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ asset records
┌─────────────────────────────────▼───────────────────────────────┐
│  LAYER 3 – MOTION PRESET LAYER                                  │
│  pipeline/motion_presets/ – MotionPreset dataclass +            │
│                             10 built-in presets                  │
│  Presets are reusable across asset categories and export         │
│  targets; they describe animation parameters, not rendering.     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ asset + preset
┌─────────────────────────────────▼───────────────────────────────┐
│  LAYER 4 – EXPORT PIPELINE                                      │
│  pipeline/exporters/  – Per-format export drivers               │
│  renders/             – Output tree (gif/ webp/ webm/ mov/ …)   │
│  One base asset → multiple outputs via export_all()             │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ rendered files
┌─────────────────────────────────▼───────────────────────────────┐
│  LAYER 5 – PRODUCT / PACK GENERATION                            │
│  pipeline/packager/   – PackDefinition + build_pack()           │
│  packs/               – Per-pack JSON definitions               │
│  Pack assembly is metadata-driven (no hardcoded file lists)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repository Layout

```
stixmagic-bot/
├── main.py              ← Bot entry-point (Layer 1)
├── api.py               ← Flask REST API + web UI
├── menus.py             ← Inline keyboard registry
├── domain/              ← Bot media processing (Pillow, ffmpeg)
├── infra/               ← SQLite persistence layer
├── static/              ← Landing page + Mini App HTML
│
├── pipeline/            ← Visual asset pipeline (Layers 2–5)
│   ├── asset_model/     ← Asset dataclass, enums
│   ├── metadata/        ← AssetCatalog (JSON I/O)
│   ├── motion_presets/  ← 10 built-in MotionPreset definitions
│   ├── exporters/       ← GIF / WebP / WebM / MOV / PNG / thumb
│   └── packager/        ← PackDefinition + build_pack()
│
├── assets/              ← Raw and processed asset files
│   ├── source/          ← Category sub-directories (letters, …)
│   ├── processed/       ← Normalised base assets
│   └── previews/        ← Static preview images
│
├── renders/             ← Export pipeline outputs
│   ├── gif/
│   ├── webp/
│   ├── webm/
│   ├── mov/
│   ├── png_sequences/
│   └── thumbnails/
│
├── packs/               ← Per-pack JSON metadata
│   ├── motion_alphabet/
│   ├── neon_signals/
│   ├── dj_pack/
│   ├── cloud_pack/
│   └── overlay_starter/
│
├── integrations/        ← Future integration scaffolding
│   ├── extension/       ← Browser / Nebulosa extension (future)
│   ├── overlay_engine/  ← OBS-style compositor (future)
│   └── virtual_camera/  ← Virtual camera output (future)
│
└── docs/                ← Architecture and developer guides
```

---


## Core vs Plugin Boundary

The repository now distinguishes between the shared Stix Magic runtime and partner/community plugins:

- `src/bot`, `src/stickers`, and `src/animations` own shared bot, sticker, timing, sphere, and export behavior.
- `src/core` and `src/config` define runtime boundaries, plugin registration, and environment namespaces.
- `src/plugins/truck_club` is reserved for The Truck Club-specific behavior so those rules do not leak into the general bot layer.

Existing top-level modules remain available as entrypoints or compatibility imports, but the architectural source of truth is the `src/` layout.

## Design Principles

1. **Preserve the bot** — `main.py` and its dependencies are never modified by the pipeline.
2. **Separation of concerns** — Exporters don't import from `main.py`; the bot doesn't import from `pipeline/`.
3. **Metadata-driven** — Pack contents are declared in JSON, not in code.
4. **Modular presets** — Animation behaviour is described once in `motion_presets/` and reused everywhere.
5. **One base asset → many outputs** — `export_all()` in `exporters/` produces every format from a single source.
6. **Placeholder-first** — Unimplemented exporters write stub files and log warnings rather than raising errors silently.
