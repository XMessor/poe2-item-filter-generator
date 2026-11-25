---
name: poe2-developer-guide
description: Technical architecture, zero-dependency Python tech stack, intentionally verbose coding philosophy, RePoE data normalization, and file-by-file module reference for XMessor's Simplified Item Filter Generator.
status: production
---

# Developer & Architecture Guide

This guide explains the technical design of **XMessor's Simplified Item Filter Generator** (`v1.0`): what runtime stack it requires, how data flows from RePoE snapshots to `.filter` files, and what every file in `engine/`, `engine/rulegen/`, and `config/` does.

---

## 1. Coding Philosophy: Intentionally Verbose by Design

As noted in the [Preface](README.md#preface), I started writing code back when the year still began with a `1`, and after passing my university programming exams I turned toward physics rather than software engineering.

That shapes every module in this repository:

* **Explicit over clever:** Functions spell out each logical step in plain Python rather than hiding intent behind dense comprehensions, metaprogramming, or deep inheritance trees.
* **`WHAT / WHY / HOW` docstrings:** Every module and major section opens with a structured header explaining *what* it produces, *why* that design choice was made, and *how* the pieces connect.
* **Immutable data records:** Core structures (`BaseItem`, `Condition`, `CellSpec`, `Rule`, `EquipBase`, `Target`, `Finding`) are frozen `@dataclass(frozen=True)` records so state flows cleanly without unexpected side effects.
* **Traceable failure handling:** Engine functions wrap operations in explicit `try / except` blocks that log contextual inputs to `.log/engine.log` via `engine.logsetup` before re-raising.

---

## 2. Tech Stack & Runtime Requirements

| Component | Requirement / Choice | Notes |
|---|---|---|
| **Language** | **Python 3.11+** *(developed & tested on Python 3.12)* | Uses `tomllib` from the standard library (introduced in Python 3.11). |
| **External packages** | **None (`0` third-party dependencies)** | No `pip install` or virtual environment required. Uses only standard library modules (`tomllib`, `csv`, `json`, `re`, `dataclasses`, `pathlib`, `argparse`, `collections`, `logging`, `subprocess`). |
| **Data source** | **Reduced item catalog** (`data/catalog_<version>.json`), built from the **RePoE PoE2** export | Players build from the catalog shipped in the repository, offline. The maintainer downloads the full RePoE snapshots (`base_items.json`, `item_classes.json`) into `.infodump/` (not part of the repository: RePoE's data files may not be redistributed, see `NOTICE.md`) and exports the catalog from them. |
| **OS / Shell** | Windows 11 / PowerShell *(cross-platform Python)* | Writes deterministic UTF-8 `.filter` files with Unix (`\n`) line endings and no timestamps so consecutive builds diff cleanly. |
| **Logging** | `.log/engine.log` | Shared rotating/appended engine log configured in `engine/logsetup.py`. |

### Why Commands Use `python -E -s`
Every CLI command invokes Python with `-E -s` (ignore environment variables and user site-packages) instead of `-I` (isolated mode). Unlike `-I`, `-E -s` keeps the current working directory on `sys.path`, allowing `python -E -s -m engine.<module>` to import the `engine` package cleanly from the project root without interference from external Python packages.

---

## 3. Pipeline Architecture & Data Flow

The generator runs in two clear stages:

```text
Stage A — Maintainer update (on game patches / RePoE updates)
  engine/fetch.py                  (RePoE snapshot -> .infodump/)
  RePoE base_items.json + config/structure.toml
    ├─> engine/rulegen/regen_all.py
    │     └─> writes 5 generated config/band_rules_*.csv files
    │         (hand-edited CSVs and config/overrides.csv are untouched)
    └─> engine/catalog.py --export
          └─> writes data/catalog_<version>.json (reduced catalog)

Stage B — Filter Compilation (every build, maintainer and players)
  catalog (RePoE snapshot if present, else data/catalog_<version>.json)
  + config/ with an optional profile on top (profiles/<name>/)
    └─> engine/build.py
          ├─> engine/profile.py    (layered config: profile files first, structure.toml merged)
          ├─> engine/catalog.py    (normalize items -> BaseItem Catalog)
          ├─> engine/config.py     (read-only validation; aborts on any error)
          ├─> engine/sections.py   (CSV + overrides -> merged Rule lists)
          ├─> engine/equipment.py  (equipment tiering, salvage, jewellery -> Rule lists)
          ├─> engine/rules.py      (shared Condition / Rule intermediate model)
          └─> engine/render.py     (Rule lists -> 20 deterministic .filter files)
```

---

## 4. RePoE Data Source & Field Semantics (`engine/catalog.py`)

RePoE exports (`https://repoe-fork.github.io/poe2/`) contain raw game data, including legacy PoE1 items and unreleased placeholders. `engine/catalog.py` normalizes two JSON snapshots (`base_items` and `item_classes`) into a single read-only `Catalog` so no downstream module has to handle raw RePoE quirks:

* **Released items only:** Keeps entries where `release_state == "released"` and drops placeholder names starting with `[DNT`.
* **Class mapping:** Resolves internal RePoE `item_class` IDs (e.g., `Bow`) to filter `Class` names (e.g., `Bows`) via `item_classes.json`.
* **Deduplication:** If the same base name appears multiple times in a class, `catalog.py` collapses it to its lowest `drop_level`.
* **Drop level vs. player level:** In RePoE, `drop_level` is the **area level** where an item can begin dropping, whereas `requirements.level` is the **player level requirement** (which can be `null` on flasks or starter gear; `equipment.py` falls back to `drop_level` when `level_requirement` is missing).
* **Attribute & defence groups:**
  * Armour items often lack attribute requirements on level-1 bases, so `catalog.py` extracts `attribute_group` (`str`, `dex_int`, etc.) from `<attr>_armour` tags on armour and falls back to `requirements` (`strength`, `dexterity`, `intelligence`) on weapons.
  * `defence_group` (`armour`, `evasion`, `energy_shield`) is derived from base properties so `_droplevel` outputs can emit `BaseArmour`, `BaseEvasion`, and `BaseEnergyShield` conditions.

### The Reduced Catalog (`data/catalog_<version>.json`)

`engine.catalog --export` writes the normalized `Catalog` (only the fields the engine uses) as one JSON file: a header (`version`, `source`, `item_classes`), then one base per line, so a version update reads as a line diff. `load_catalog()` uses the RePoE snapshot when it exists (the maintainer's source of truth) and the reduced catalog otherwise; both give identical records, so a build from either source is byte-identical. The version comes from `--repoe-version`, or from `structure.toml` `[repoe] version` when the switch is omitted.

---

## 4a. The Profile Layer (`engine/profile.py`)

A player profile (`--profile profiles/<name>`) holds only the files the player changed. `ConfigLayers` answers `config_dir / "file.csv"` like a folder would, returning the profile's copy if there is one and the `config/` file otherwise, so the section builders and the validator work unchanged. `load_config()` deep-merges the profile's `structure.toml` over the default one: tables merge key by key, any other value replaces the default whole. `engine.config` warns about profile files that no setting refers to.

---

## 5. File-by-File Reference

### A. Filter Compiler (`engine/`)

| File | Status | Responsibility |
|---|---|---|
| `engine/__init__.py` | Implemented | Package marker and CLI invocation docstring. |
| `engine/logsetup.py` | Implemented | Sets up the shared `engine` logger writing to `.log/engine.log`. |
| `engine/catalog.py` | Implemented | Loads and normalizes RePoE `base_items` and `item_classes` into `BaseItem` records and `Catalog` lookup methods, or reads the reduced catalog; `--export` writes `data/catalog_<version>.json`. Runnable standalone for class inspection. |
| `engine/profile.py` | Implemented | The profile layer: `ConfigLayers` (profile-first file lookup), `load_config()` (`structure.toml` deep merge). |
| `engine/config.py` | Implemented | Read-only TOML/CSV loader and strict validator: checks UTF-8 BOM/ASCII-only bytes, band column headers, cell syntax (`CELL_PATTERN`), `match`/`rarity`/`family`/`item_class` values, item presence in RePoE, `-` cells vs. `drop_level`, duplicate/shadowed rows, `overrides.csv` 1-to-1 target matching, and `structure.toml` colours/icons/sections. Exits with code `1` on any error. |
| `engine/rules.py` | Implemented | Defines the intermediate filter model (`Condition`, `CellSpec`, `Rule`) and `parse_cell()`, decoupling section logic from filter output syntax. |
| `engine/sections.py` | Implemented | Loads per-band CSVs, applies `config/overrides.csv`, handles special `band_rules_gold.csv` stack thresholds, merges identical style keys into compact `BaseType` lists, and emits explicit `Hide` rules for every `H` cell. |
| `engine/equipment.py` | Implemented | Computes 4-tier base progression per attribute group (`min_group_size` merging), `ItemLevel` endgame windows, `base_exceptions.csv` `+1` boosts, rare scaling, `salvage_rules` / `with_salvage` (also reused by `flasks`), `_droplevel` range merging (`Target`), and `build_jewellery()`. |
| `engine/render.py` | Implemented | Translates `Rule` lists into deterministic Path of Exile 2 syntax (`Show`/`Hide`, `AreaLevel` bounds, font size, colours, black background, level-5 inverse, `PlayAlertSound`, `PlayEffect`, `MinimapIcon`), producing both the combined `AreaLevel` file and per-band files. |
| `engine/build.py` | Implemented | CLI entry point: loads the layered config, builds `Catalog`, runs `validate()`, compiles all sections in both `"names"` and `"droplevel"` modes, and writes the 20 `.filter` files. |
| `engine/simulate.py` | Implemented | Passes every catalog base across every band through the compiled rules: lists the classes that reach the catch-all, and every item where the names and `_droplevel` builds disagree (exit code `1` on any disagreement). |
| `engine/diff.py` | Implemented | Compares two catalog versions (added, removed, changed bases and classes) and lists the added bases that reach the catch-all; `--config-before` adds the rule CSV rows that regeneration changed. Maintainer tool. |
| `engine/fetch.py` | Implemented | Reads the online RePoE version and downloads its snapshot into `.infodump/` (validated JSON, staging folder, no overwrite without `--force`). Maintainer tool. |

### B. Rule CSV Generators (`engine/rulegen/`)

| Script | Output File | How It Works |
|---|---|---|
| `regen_all.py` | *(all 5 generated CSVs)* | Runs all five generators below in subprocesses (`--out-dir` supports regression checks against `config/`; `--dry-run` prints without writing). |
| `build_gem_rules.py` | `config/band_rules_gems.csv` | Builds rows for Uncut Skill/Spirit gems (top 2 levels visible), Support gems (top level visible, dropping to `0` from band `76+`), and exact/ASCII-matched Lineage support gems (`level 4`). |
| `build_map_rules.py` | `config/band_rules_map_items.csv` | Generates `T1–T16` Waystone rows via moving `WAYSTONE_WINDOWS` plus class rows for `Tablet`, `Pinnacle Keys`, `Vault Keys`, `Relics`, and `Trial Coins`. |
| `build_league_rules.py` | `config/band_rules_league.csv` | Matches `StackableCurrency` and `BrequelFruit` RePoE items against ordered regex `GROUPS` (first match wins) and uses `ascii_match()` for non-ASCII names. Provides shared helpers imported by `build_gem_rules.py` and `build_socketable_rules.py`. |
| `build_socketable_rules.py` | `config/band_rules_socketables.csv` | Matches RePoE `SoulCore` items (runes, soul cores, idols, `@65` named socketables) using `build_league_rules.run()`. |
| `build_flask_rules.py` | `config/band_rules_flasks.csv` | Emits the best `LifeFlask` and `ManaFlask` bases per band (skipping bases with `drop_level < 10`), `Rare` `Charms` at level `1`, and explicit `Hide` for `Normal`/`Magic` Charms. |

### C. Configuration Directory (`config/`)

| File(s) | Role |
|---|---|
| `structure.toml` | Master structural config: RePoE path pattern, output filenames, 9 bands, section order, importance scale, `default_background`, 16 sound families, colour categories, attribute borders, salvage thresholds, equipment & jewellery parameters. |
| `overrides.csv` | Update-safe manual overrides applied to matching rows across any band rule CSV before building. |
| `base_exceptions.csv` | Implicit prefix exceptions granting `+1` tier boosts (capped at `3` for Normal/Magic, `4` for Rare). |
| `jewellery.csv` | Explicit border and minimap colour rules per Ring/Amulet base (`*` for all Belts). |
| `band_rules_{unique,currency,jewels_quest,gold,catch_all}.csv` | Hand-edited rule CSVs (direct sources of truth). |
| `band_rules_{gems,league,socketables,flasks,map_items}.csv` | Script-generated rule CSVs (regenerated via `engine/rulegen/regen_all.py`). |

---

## 6. Developer CLI Reference (Windows PowerShell)

Run all commands from the repository root. Every command takes `--repoe-version <version>`; without it the version in `structure.toml` `[repoe] version` is used. `build`, `config` and `simulate` also take `--profile profiles/<name>`.

```powershell
# 1. Inspect the catalog summary by class
python -E -s -m engine.catalog

# 2. Validate structure.toml + all CSVs + overrides.csv against the catalog
python -E -s -m engine.config

# 3. Dry-run filter build (prints block counts per section)
python -E -s -m engine.build --dry-run

# 4. Build all 20 filter files to a custom folder or specific sections only
python -E -s -m engine.build --out tmp/test_build --only unique,currency,equipment

# 5. Catch-all and names/droplevel audit (about a minute)
python -E -s -m engine.simulate
```

Maintainer commands (they need the RePoE snapshot in `.infodump/`):

```powershell
# Online RePoE version, stored versions, download (--dry-run: report only)
python -E -s -m engine.fetch --dry-run

# Regenerate the 5 script-driven rule CSVs (--dry-run: no files written)
python -E -s engine/rulegen/regen_all.py .infodump/repoe_poe2_0.5.5.9_base_items.json --dry-run

# Write the reduced catalog data/catalog_<version>.json
python -E -s -m engine.catalog --repoe-version 0.5.5.9 --export

# What changed between two versions, and which new bases reach the catch-all
python -E -s -m engine.diff --old-version 0.5.5.9 --new-version <new> --report tmp/repoe_diff.md
```
