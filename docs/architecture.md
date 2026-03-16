# MagicStix — Architecture Overview

> **Version:** 1.0 · **Updated:** 2026-03

This document describes the five-layer architecture of the MagicStix visual
asset platform.  The bot remains the primary interface for end-users, while the
pipeline, asset registry, motion preset system, export pipeline, and pack
generator collectively transform individual base assets into multi-format
animated outputs.

---

## Layer Map

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — BOT                                                  │
│  Telegram bot (python-telegram-bot v21)                         │
│  main.py · menus.py · infra/db.py · domain/media.py · api.py   │
│  → generates base assets (PNG/WebP stickers)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ base assets
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2 — ASSET & METADATA                                     │
│  pipeline/asset_model/   pipeline/metadata/                     │
│  Asset dataclass         AssetRegistry (JSON-backed)            │
│  → indexed, searchable, tag-annotated asset catalog             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Asset objects
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3 — MOTION PRESETS                                       │
│  pipeline/motion_presets/                                       │
│  MotionPreset dataclass   10 built-in presets                   │
│  → reusable, parameter-driven animation descriptors             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ (Asset, MotionPreset) pairs
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4 — EXPORT PIPELINE                                      │
│  pipeline/exporters/                                            │
│  GIF · animated WebP · WebM · MOV · PNG sequence · thumbnail    │
│  → renders/gif/ · renders/webp/ · renders/webm/ · …            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ ExportResult lists
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5 — PRODUCT / PACK GENERATION                            │
│  pipeline/packager/  +  packs/<pack_id>/pack.json               │
│  Pack dataclass   PackGenerator                                 │
│  → self-describing product packs driven by metadata             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
stixmagic-bot/
├── main.py                  # Bot orchestration + conversation handlers
├── menus.py                 # Inline menu system (MENU_STRUCTURE)
├── api.py                   # Flask REST API
├── domain/
│   └── media.py             # Image/video processing (Pillow, ffmpeg)
├── infra/
│   └── db.py                # SQLite persistence layer
│
├── pipeline/                # ← NEW: Visual asset pipeline
│   ├── asset_model/         # Asset + category/theme/format constants
│   ├── metadata/            # JSON-backed AssetRegistry
│   ├── motion_presets/      # MotionPreset dataclass + 10 built-in presets
│   ├── exporters/           # GIF / WebP / WebM / MOV / PNG / thumbnail
│   └── packager/            # Pack dataclass + PackGenerator
│
├── assets/                  # ← NEW: Source asset library
│   ├── source/
│   │   ├── letters/         # Base letter assets (JSON descriptors + PNGs)
│   │   ├── numbers/
│   │   ├── emojis/
│   │   ├── symbols/
│   │   ├── signals/
│   │   ├── frames/
│   │   └── particles/
│   ├── processed/           # Post-processed / composited base assets
│   └── previews/            # Static preview images for the catalog
│
├── renders/                 # ← NEW: Pipeline output files
│   ├── gif/
│   ├── webp/
│   ├── webm/
│   ├── mov/
│   ├── png_sequences/
│   └── thumbnails/
│
├── packs/                   # ← NEW: Product pack descriptors
│   ├── motion_alphabet/pack.json
│   ├── neon_signals/pack.json
│   ├── dj_pack/pack.json
│   ├── cloud_pack/pack.json
│   └── overlay_starter/pack.json
│
├── integrations/            # ← NEW: Future integration scaffolding
│   ├── extension/           # Browser / Nebulosa extension
│   ├── overlay_engine/      # OBS-style lightweight compositor
│   └── virtual_camera/      # Virtual camera output
│
├── docs/                    # ← NEW: Architecture documentation
│   ├── architecture.md      # This file
│   ├── pipeline.md
│   ├── asset_schema.md
│   ├── motion_system.md
│   ├── export_formats.md
│   ├── pack_generation.md
│   └── future_integrations.md
│
└── static/                  # Web assets (landing page, Mini App, API docs)
```

---

## Data Flow: One Asset → Multiple Outputs

```
┌──────────────┐    ┌─────────────┐    ┌──────────────────────────────────┐
│  Base Asset  │ ×  │  Motion     │ →  │  Export Pipeline                 │
│  letter_a    │    │  Preset     │    │  ┌──────────┐  ┌──────────────┐  │
│  (PNG/WebP)  │    │  "pulse"    │    │  │ GIF      │  │ animated WebP│  │
└──────────────┘    └─────────────┘    │  ├──────────┤  ├──────────────┤  │
                                        │  │ WebM+α  │  │ MOV+α        │  │
                                        │  ├──────────┤  ├──────────────┤  │
                                        │  │ PNG seq  │  │ thumbnail    │  │
                                        │  └──────────┘  └──────────────┘  │
                                        └──────────────────────────────────┘
                                                        │
                                                        ▼
                                        ┌──────────────────────────────────┐
                                        │  Pack Inclusion                  │
                                        │  motion_alphabet pack.json       │
                                        │  → asset_id in included_assets   │
                                        └──────────────────────────────────┘
```

---

## Key Design Principles

1. **One base asset, many outputs** — a single source PNG/WebP can generate
   GIF, animated WebP, WebM, MOV, and PNG sequence outputs by pairing with
   any compatible motion preset.

2. **Metadata-driven packs** — product packs are described by JSON files, not
   by hardcoded file lists.  The pack generator resolves assets and presets
   at generation time.

3. **Exporter independence** — exporters do not depend on the bot.  They
   consume `Asset` and `MotionPreset` objects and write files to `renders/`.

4. **Preset reusability** — a motion preset is defined once and can be applied
   to any number of assets across any number of packs.

5. **Placeholder safety** — all exporters are marked as placeholder
   implementations.  They write stub files so the pipeline can be exercised
   end-to-end before real rendering code is written.

6. **Future compatibility** — the `integrations/` stubs reserve namespaces
   for the overlay engine, browser extension, and virtual camera without
   requiring any implementation now.

---

## Component Responsibilities

| Component | Responsibility |
|---|---|
| `main.py` | Bot conversation handlers; drives sticker creation via Telegram |
| `domain/media.py` | Pillow / ffmpeg media processing for sticker formats |
| `infra/db.py` | SQLite CRUD for packs and user settings |
| `api.py` | Flask REST API for external access |
| `pipeline/asset_model/` | Defines what an asset is (data model only) |
| `pipeline/metadata/` | Loads and indexes asset descriptors from JSON files |
| `pipeline/motion_presets/` | Defines animation presets and their parameters |
| `pipeline/exporters/` | Renders (asset + preset) pairs to disk in each format |
| `pipeline/packager/` | Loads pack descriptors and orchestrates batch exports |
| `integrations/` | Placeholder stubs for future overlay / extension / camera |

---

## See Also

- [`pipeline.md`](pipeline.md) — detailed pipeline walkthrough
- [`asset_schema.md`](asset_schema.md) — JSON asset descriptor schema
- [`motion_system.md`](motion_system.md) — motion preset system
- [`export_formats.md`](export_formats.md) — supported export formats
- [`pack_generation.md`](pack_generation.md) — pack generation guide
- [`future_integrations.md`](future_integrations.md) — integration roadmap
