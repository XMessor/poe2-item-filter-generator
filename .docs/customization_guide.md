---
name: poe2-customization-guide
description: Step-by-step guide to customizing XMessor's Simplified Item Filter Generator without writing code—in a profile folder layered over config/, using overrides.csv, band_rules_*.csv tables, base_exceptions.csv, jewellery.csv, and structure.toml, then validating and rebuilding the filters.
status: production
---

# Customization Guide

You do not need to touch a single line of Python code to tailor **XMessor's Simplified Item Filter Generator** to your playstyle or build. Every rule, colour, font size, sound, and threshold lives in human-readable configuration files: the defaults in `config/`, your changes in your own **profile**.

---

## 0. Your Profile: Change Only What You Need

Do not edit `config/` itself: it holds the defaults, and it changes whenever this repository is updated. Put your changes in a profile folder instead:

```text
profiles/my_profile/
  structure.toml     only the keys you change
  overrides.csv      single cells of single items
  <any config file>  a full copy, only if you rewrite that file
```

How the layers combine:

* **A file in your profile replaces the default file with the same name.** A file you do not have comes from `config/`, so it keeps receiving updates.
* **`structure.toml` is merged, not replaced.** Write only the keys you change; tables merge key by key. Any other value you write (a list, a string, a number) replaces the default whole. For example, a `bands` list in your profile replaces all bands.
* **Prefer `overrides.csv` to copying a whole CSV.** A copied CSV no longer receives updates (new items, fixes). An override row changes only the cells you name.
* **Misspelt file names are reported.** `engine.config` warns about any profile file that no setting refers to, because the build would ignore it.

Example: smaller labels at the lowest importance level, and nothing else changed:

```toml
# profiles/my_profile/structure.toml
[importance.0]
font_size = 16
```

Folders under `profiles/` are not part of the repository (except `profiles/README.md`), so updating the repository never touches them.

---

## 1. The Easiest & Update-Safe Way: `overrides.csv`

Five of the per-band CSV tables (`gems`, `league`, `socketables`, `flasks`, `map_items`) are generated automatically from RePoE data by scripts in `engine/rulegen/`, and they are regenerated for every game patch.

Put personal adjustments to single items into **`profiles/<name>/overrides.csv`** (copy the header line from `config/overrides.csv`). Overrides are applied *on top* of any section's table (generated or hand-edited) right before the filter is built, so your changes survive future updates cleanly.

### Column Layout
```text
section,name,match,item_class,rarity,gem_level,waystone_tier,family,category,1-15,16-30,31-45,46-60,61-70,71-75,76-80,81-85,86-99,note
```

* **Target key (must match exactly one row):** `section` (matching a name from `[output] sections` in `config/structure.toml`), plus the six identity columns (`name`, `match`, `item_class`, `rarity`, `gem_level`, `waystone_tier`). Leave a key column empty where the target row leaves it empty.
* **Columns you can override:** `family`, `category`, or any progression band (`1-15` through `86-99`), plus `note` to remind yourself why you changed it.
* **Empty cells keep the original value:** Only fill in the specific cells you want to change.
* **Validation guarantee:** Every override row must match **exactly one** existing target row—if a name has a typo or matches zero/multiple rows, `engine.config` catches it and stops before building. *(Overrides modify existing rows; to add a brand-new item rule, add a row to a hand-edited CSV.)*

### Example: Highlighting `Omen of Light` in Band `86–99`
To promote `Omen of Light` to jackpot level `5` with a light beam (`5b`) in the `86–99` band while keeping all earlier bands untouched:

```csv
league,Omen of Light,exact,,,,,,,,,,,,,,,5b,example: boost in top endgame
```

---

## 2. Editing Per-Band Rule Tables (`config/band_rules_*.csv`)

If you want to overhaul whole categories or add new rules, copy the file into your profile and edit the copy. Check first whether the file is **hand-edited** (a copy is fine) or **script-generated** (prefer `overrides.csv`, because a copy misses the regenerated rows of later patches):

| File | Source of Truth | What It Controls |
|---|---|---|
| `band_rules_unique.csv` | Hand-edited | Global `Unique+` rule (first section of the filter) |
| `band_rules_currency.csv` | Hand-edited | Currency orbs, shards, and exotic drops |
| `band_rules_jewels_quest.csv` | Hand-edited | Time-Lost jewels, standard jewels, and Quest Items |
| `band_rules_gold.csv` | Hand-edited | Gold minimum `StackSize` thresholds per band |
| `band_rules_catch_all.csv` | Hand-edited | Final safety-net rule at the bottom of the filter |
| `band_rules_gems.csv` | Script-generated | Uncut Skill/Spirit/Support gems & Lineage supports |
| `band_rules_league.csv` | Script-generated | Essences, catalysts, liquids, Expedition, splinters, keys, bones, omens |
| `band_rules_socketables.csv` | Script-generated | Runes, soul cores, idols, and named `@65` socketables |
| `band_rules_flasks.csv` | Script-generated | Life/Mana flasks and Charms |
| `band_rules_map_items.csv` | Script-generated | Waystones, Tablets, Pinnacle/Vault keys, Relics, Trial Coins |

### Cell Syntax (`0–5`, `b`, `i`, `H`, `-`)
Every band cell (`1-15` … `86-99`) follows a strict ASCII notation:

| Cell Value | Meaning | Example |
|---|---|---|
| `0`–`5` | Show at importance level `0` (minimal) through `5` (inverse jackpot) | `3` |
| `b` | Add a permanent light beam (`PlayEffect`) using the category's named colour | `3b` |
| `i` | Add a minimap icon (`MinimapIcon`) using the family's shape and volume-based size | `3i` or `4bi` |
| `H` | Emit an explicit `Hide` block in this band (keeps the item out of `Catch-all`) | `H` |
| `-` | Item cannot drop in this band (`drop_level > band_max`, checked against RePoE) | `-` |

### Special Table: `band_rules_gold.csv`
In `band_rules_gold.csv`, the band cells hold the **minimum `StackSize`** for that row's importance level (`level` column), while `sound` (`yes`/`no`) and `border` (`yes`/`no`) control exceptions per level:
* `0` means "every stack size".
* Any gold pile smaller than the lowest configured threshold in that band is automatically hidden.

### Crucial Rule: Keep CSVs Pure ASCII (No UTF-8 BOM)
Windows Excel often corrupts non-ASCII characters in UTF-8 CSV files that lack a BOM, so the validator rejects any non-ASCII byte or BOM marker in `config/*.csv`.
* Never save with a UTF-8 BOM (`Excel CSV UTF-8` adds a BOM—use standard ASCII CSV or a plain-text editor).
* If a Path of Exile 2 item name contains non-ASCII letters (such as `Legacy of Mjölner` or `Mórrigan's Insight`), set `match` to `contains` and enter the longest unique ASCII substring (e.g., `Legacy of Mj` or `rrigan's Insight`).

---

## 3. Customizing Equipment, Implicit Exceptions & Jewellery

The CSV files below go into your profile as copies; the `structure.toml` keys go into your profile's `structure.toml` on their own.

* **`config/base_exceptions.csv` (Implicit `+1` Tier Boosts):**
  Each row grants an importance boost (typically `+1`, capped at level `3` for Normal/Magic and `4` for Rare) to any item in `item_class` whose RePoE implicit ID starts with `implicit_prefix` (omitting the trailing tier digit so future tiers match automatically).
  ```csv
  implicit_prefix,item_class,label,effect
  BowImplicitAdditionalArrows,Bow,additional arrow,+1
  ```
* **`config/jewellery.csv` (Ring, Amulet & Belt Borders):**
  Controls border and minimap icon colours per base name (or `*` for a whole class such as `Belt`). Named rows are evaluated before `*` class rows.
* **Equipment & Salvage Tuning (`config/structure.toml`):**
  * Under `[equipment]`: adjust `endgame_floor` (default `75`), `min_group_size` (default `4`), `rare_max_level`, `rare_outdated_campaign` (`0`), `rare_outdated_endgame` (`1`), or `item_level_windows` for `76+` bands.
  * Under `[salvage]`: adjust `thresholds` (`up_to`, `quality`, `sockets`), `high_quality` (`13`), `medium_quality` (`7`), or salvage border RGB colours (`quality`, `socket`, `quality_and_socket`).

---

## 4. Customizing Theme, Colours, Font Sizes & Sounds (`config/structure.toml`)

`config/structure.toml` controls the entire look and feel of the generated filters. Write the keys you change into `profiles/<name>/structure.toml`:

* **`[importance.0]` … `[importance.5]`:** Change `font_size`, alert `volume` (`0`, `50`, `100`, `200`), or toggle `inverse = true` / `inverse_text` under `[style]`. *(Avoid using `32` so unfiltered items remain immediately recognizable.)*
* **`[icon_size_by_volume]`:** The minimap icon size (`0` largest … `2` smallest) is chosen by alert volume, so **every volume you use needs a key here**; `engine.config` reports a missing one as an error. Example for a level-2 volume of `25`: `25 = 2`.
* **`[style]`:** Adjust `default_background` (`"0 0 0 235"`, the background of every visible label).
* **`[families.1]` … `[families.16]`:** Adjust the minimap `icon_shape` (`Circle`, `Diamond`, `Hexagon`, `Square`, `Star`, `Triangle`, `Cross`, `Moon`, `Raindrop`, `Kite`, `Pentagon`, `UpsideDownHouse`) or default `category` per sound ID.
* **`[categories.*]` & `[attributes.*]`:** Edit `text` and `border` as `"R G B A"` strings (`0–255`), and `icon` using one of the 11 game-supported named colours (`Red`, `Green`, `Blue`, `Brown`, `White`, `Yellow`, `Cyan`, `Grey`, `Orange`, `Pink`, `Purple`).
* **`[output]`:** Rename output files, adjust the 9 progression `bands`, or reorder `[output] sections` *(keep `unique` first and `catch_all` last)*.

---

## 5. Validating & Rebuilding Your Filters (Windows PowerShell)

After editing your profile, run the validator and builder from the repository root. Note the `-E -s` Python flags—they isolate Python from external environment variables while still allowing Python to import the `engine` package from the current working directory.

### Step 1: Validate Your Profile (Read-Only)
```powershell
python -E -s -m engine.config --profile profiles/my_profile
```
If there is a typo, a non-ASCII character, a broken cell token, or an `overrides.csv` row that does not match a target, this prints the exact file and line number and exits with code `1` before touching any output. A profile file that no setting uses is reported as a warning.

### Step 2: Preview Block Counts (Dry Run)
```powershell
python -E -s -m engine.build --profile profiles/my_profile --dry-run
```
Compiles every section in memory and prints block counts without writing files to disk.

### Step 3: Build All 20 Filter Files
```powershell
python -E -s -m engine.build --profile profiles/my_profile
```
Writes the `v1.0_area_level.filter` file, the 9 per-band `.filter` files, and all 10 `_droplevel.filter` variants into your profile's `filters/` folder (a profile build never writes into the repository's `filter_samples/`). Copy the ones you want into your game folder ([README](../README.md#install-a-filter-windows)); [`filter_samples/README.md`](../filter_samples/README.md) explains which file does what.

Optional useful flags:
* `--out <folder>` — Write somewhere else than `profiles/<name>/filters/`.
* `--only currency,equipment` — Build only a comma-separated subset of sections for quick testing.
* `--repoe-version <version>` — Build from another catalog version than the one in `structure.toml` `[repoe] version`.

### Optional: Check for Items the Filter Misses
```powershell
python -E -s -m engine.simulate --profile profiles/my_profile
```
Runs every catalog base through your rules in every band (about a minute) and lists the classes that reach the catch-all.

---

*Want to understand how the Python engine itself works under the hood or how RePoE snapshots feed the generator? Continue to the **[Developer & Architecture Guide](developer_guide.md)**.*
