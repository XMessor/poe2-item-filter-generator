---
name: v1-0-filter-engine
description: The v1.0 loot filter engine - catalog, profile layer, config validation, rule model, section builders, renderer, simulator, RePoE diff and fetch; plus rulegen, the generators of the rule CSVs.
status: incubation
clean_runs: 0/10
created: 2026-11-14
---

# engine

The v1.0 filter engine: zero-dependency Python 3.11+. The full guide, with the data flow and a
file-by-file reference, is the [Developer & Architecture Guide](../.docs/developer_guide.md);
the settings are in [`../config/`](../config/).

## Modules

| # | Module | Job |
|---|---|---|
| 1 | `catalog.py` | Item catalog: RePoE snapshot → `BaseItem` records (name, filter class, drop level, level requirement, attribute group, implicits, defence group), without `[DNT` and unreleased items. `--export` writes the reduced catalog `data/catalog_<version>.json`, which is read when no RePoE snapshot is present. |
| 2 | `config.py` | Reads and validates the TOML and CSV files (cell syntax, band headers, ASCII, families, categories, names against the catalog, overrides, unused profile files). Exit code `1` on any error. |
| 3 | `rules.py` | Intermediate model: `Rule` (conditions, band, level, beam/icon, family, category). |
| 4 | `sections.py` | CSV sections → `Rule`s, including `GemLevel`, `WaystoneTier`, Gold `StackSize`, `overrides.csv` and explicit `Hide` rules. |
| 5 | `equipment.py` | Equipment: tiers, implicit exceptions, `ItemLevel`, rares, salvage, jewellery, flask salvage. |
| 6 | `render.py` | `Rule` → filter text: the AreaLevel file and the per-band files, each also as a `_droplevel` variant (20 files). |
| 7 | `simulate.py` | Every catalog item in every band through the rules: what reaches the catch-all, and where the names and `_droplevel` builds disagree. |
| 8 | `diff.py` | Two catalog versions compared; the added bases that reach the catch-all (the decision list); `--config-before`: the changed CSV rows. |
| 9 | `build.py` | Entry point (`--profile`, `--config`, `--out`, `--only`, `--repoe-version`, `--dry-run`); writes both modes (names, `_droplevel`). |
| 10 | `fetch.py` | The online RePoE version and its download into `.infodump/` (through a staging folder, validated JSON; never overwrites without `--force`). |
| 11 | `profile.py` | Profile layer: files in `--profile DIR` replace the `config/` files of the same name; `structure.toml` is merged key by key over the default. |
| – | `rulegen/` | The rule scripts of the generated band rule CSVs, and `regen_all.py`. |

## Rule sources

- The generated CSVs (`gems`, `map_items`, `league`, `socketables`, `flasks`) come from the rules
  in `rulegen/`. On an update `regen_all.py` rewrites them, and `diff.py` shows the change.
- The hand-written CSVs (`currency`, `jewels_quest`, `unique`, `gold`, `catch_all`) are their own
  source.
- A manual fix of a generated item goes into `overrides.csv`, which the engine applies last, so it
  survives regeneration. Format: [`../config/README.md`](../config/README.md).

## Running

From the repository root. Without `--repoe-version` the version in `structure.toml` `[repoe]
version` is used.

```
python -E -s -m engine.catalog                       # summary by class
python -E -s -m engine.catalog --repoe-version V --export [--dry-run]   # reduced catalog from RePoE
python -E -s -m engine.config  [--profile DIR]       # validation; exit code 1 on any error
python -E -s -m engine.build   [--profile DIR] [--out DIR] [--only a,b] [--dry-run]
python -E -s -m engine.simulate [--profile DIR]      # about a minute; exit code 1 on a disagreement
python -E -s -m engine.fetch [--dry-run]             # online version, stored versions, download
python -E -s -m engine.diff --old-version A --new-version B [--config-before DIR] [--report FILE]
python -E -s engine/rulegen/regen_all.py .infodump/repoe_poe2_<version>_base_items.json [--out-dir DIR] [--dry-run]
```

`-E -s` instead of `-I`, because the package is imported from the repository root. Errors are
logged to `.log/engine.log`.
