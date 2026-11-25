---
name: poe2-filtering-philosophy
description: Core filtering philosophy, section evaluation order, progression bands, item category rules, equipment base tiering, endgame ItemLevel windows, and salvage rules for XMessor's Simplified Item Filter Generator (PoE2 v1.0).
status: production
---

# Filtering Philosophy & Item Progression

Every generated Path of Exile 2 (`v1.0`) filter evaluates dropped items strictly **from top to bottom**—the **first matching block wins**. This document explains the filtering hierarchy, the exact evaluation order across all 12 item sections, and how rules adapt across the 9 progression bands.

---

## 1. Core Philosophy: Good Find → Salvage → Hide

For every item category, the filter applies a three-step decision funnel:

1. **Good Find:** High-value currency, uniques, endgame keys, and crafting bases relevant to your current progression level—along with items of sufficient rarity (`Rare` or `Unique`)—are always shown so you never miss an upgrade or valuable drop.
2. **Salvage:** Outdated `Normal` and `Magic` equipment bases (plus hidden flasks and charms) are checked for useful **Quality** or **Sockets** above band-scaled thresholds so you can collect Salvage Bench materials efficiently.
3. **Hide:** Everything else is **explicitly hidden** (`Hide`) at the end of its section to keep screen clutter away and ensure intentionally filtered items never leak down into the safety net (`Catch-all`).

---

## 2. Top-Down Evaluation Order (The 12 Sections)

Sections are always emitted in the exact priority order defined in `config/structure.toml`. Three hard rules govern this order: `Unique+` must come first, `Catch-all` must come last, and every section with hidden items closes with its own explicit `Hide` blocks.

| # | Section | What It Covers | Why Here |
|---|---|---|---|
| 1 | `unique` (`Unique+`) | All `Unique` items across every class (gear, tablets, jewels, charms, flasks) | Highest priority so a `Unique` drop is never swallowed by a base-type or class rule. |
| 2 | `currency` | Orbs, shards, crafting mats, and top-tier drops (`Divine`, `Mirror`, `Fracturing`, `Annulment`, `Hinekora's Lock`, `Starlit Ore`) | Valuable drops stand out immediately regardless of item class. |
| 3 | `league` | Essences, catalysts, Delirium liquids, Expedition artifacts/coinage, splinters, keys, desecrated bones, and omens | Specialized league crafting/collectible drops. |
| 4 | `socketables` | Runes, Soul Cores, Idols, and named `@65` socketable drops | Distinct socketable progression rules. |
| 5 | `map_items` | Waystones (tiered by `WaystoneTier`), Tablets, Pinnacle Keys, Vault Keys, Relics, and Trial Coins | Endgame progression drops before general gear. |
| 6 | `jewels_quest` | Time-Lost Jewels first, standard Jewels by rarity, and Quest Items | Time-Lost Jewels are checked first so they override generic jewel rarity rules. |
| 7 | `gems` | Uncut Skill, Spirit, and Support Gems (by `GemLevel`), plus Lineage Support Gems | Shows only progression-relevant uncut gem levels and all Lineage supports. |
| 8 | `gold` | Gold stacks filtered by `StackSize` (highest stacks first) | Small stacks are suppressed early while meaningful piles stay visible. |
| 9 | `flasks` | Life Flasks, Mana Flasks, and Charms (+ quality-only Salvage and explicit `Hide`) | Keeps only the best flask bases for the current band and `Rare` charms. |
| 10 | `jewellery` | Rings, Amulets, and Belts | Evaluated by base/implicit type rather than character level. |
| 11 | `equipment` | 22 weapon, offhand, and armour classes (`Rare` → `Normal`/`Magic` bases → Salvage → explicit `Hide`) | Core adaptive base-type, `ItemLevel`, rarity, and salvage progression. |
| 12 | `catch_all` | Any unmatched item across all classes | Safety net for brand-new or unexpected items after a game patch. |

**How bands sit inside sections:** Within each section, higher-level bands come first. In `v1.0_area_level.filter`, every block carries `AreaLevel` bounds so the active band switches dynamically by zone; in the individual `v1.0_level_XX-YY.filter` files, only that band's blocks are generated.

---

## 3. The 9 Disjoint Progression Bands

`v1.0` uses **9 disjoint level bands** so that `AreaLevel` blocks in the combined filter never conflict:

| Band | Typical Game Stage | Salvage Thresholds (`q` / `s`) | Key Shifts |
|---|---|---|---|
| `01–15` | Act 1 | `Quality > 0` or `Sockets > 0` | Almost every basic currency, shard, and crafting base is useful. |
| `16–30` | Act 2 | `Quality > 4` or `Sockets > 0` | Jewels start dropping (`@20`); first socket/quality filtering tightens. |
| `31–45` | Act 3 | `Quality > 9` or `Sockets > 1` | Early campaign shards/quality orbs fade; mid-campaign bases rotate in. |
| `46–60` | Act 4 | `Quality > 9` or `Sockets > 1` | Waystones (`T1`) and Greater currencies appear. |
| `61–70` | Early Endgame | `Quality > 9` or `Sockets > 1` | Gold thresholds stabilize (`200+`); Perfect Jeweller's & Tablets appear. |
| `71–75` | Mid Endgame | `Quality > 9` or `Sockets > 1` | Greater crafting orbs (`@72`) enter; mid-tier Waystones rotate up. |
| `76–80` | High Endgame | `Quality > 9` or `Sockets > 1` | Endgame floor (`75`) and `ItemLevel` windows activate; Support Gems drop to minimal (`0`). |
| `81–85` | Pinnacle Endgame | `Quality > 9` or `Sockets > 1` | `ItemLevel 81` and `82+` windows activate; `T16` Waystones take top priority. |
| `86–99` | Top Endgame | `Quality > 9` or `Sockets > 1` | Strictest top-end base and `ItemLevel 82+` filtering. |

---

## 4. Category Progression Rules

### Unique+ (`band_rules_unique.csv`)
* Every `Unique` item (equipment, tablets, jewels, charms, flasks) is shown at **importance level `4`** across all bands with a beam and minimap icon. Because `Unique+` is the very first section, it overrides all later class-based rules.

### Currency (`band_rules_currency.csv`)
* **Exotic drops (Family 1):** `Divine Orb`, `Fracturing Orb`, `Mirror of Kalandra`, `Hinekora's Lock`, `Orb of Annulment`, and `Starlit Ore` always stay at **level `4`–`5`** with minimap icons (and beams on the top tier).
* **Campaign vs. Greater/Perfect tiers:** Early crafting currencies (`Transmutation`, `Augmentation`, `Artificer's`, shards, `Whetstone`, `Armourer's Scrap`) step down in size/importance as you leave the opening acts, while `Greater` (`@46` / `@72`) and `Perfect` (`@72` / `@79`) orbs scale in with beams (`b`) and minimap icons (`i`).

### League Items & Socketables (`band_rules_league.csv`, `band_rules_socketables.csv`)
* **Sliding prefix tiers:** Standard **Essences** and core **Runes** shift by tier across bands (`Lesser` → standard → `Greater` → `Perfect`) so older tiers naturally step down as higher ones unlock.
* **High-value collectibles:** Special Essences (Delirium, Horror, Hysteria, Insanity, Abyss, Breach), `Potent`/`Concentrated` Delirium Liquids, high-tier Omens (`@80`), `Soul Cores`, `Idols`, and named `@65` socketables stay highlighted at **level `3`–`4`** with icons (and beams on the `@65` named socketables).

### Map & Endgame Items (`band_rules_map_items.csv`)
* **Waystones (`WaystoneTier`):** Each endgame band highlights a moving window of tiers—for example:
  * `46–60`: `T1` → `3` (icon)
  * `61–70`: `T6` → `3` (icon), `T4–5` → `2`, `T1–3` → `1`
  * `71–75`: `T10–11` → `3` (icon), `T7–9` → `2`, `T4–6` → `1`, `T1–3` → `0`
  * `76–80`: `T15–16` → `3` (icon), `T12–14` → `2`, `T9–11` → `1`, `T6–8` → `0`, `≤T5` → hidden
  * `81–99`: `T16` → `3` (icon), `T14–15` → `2`, `T11–13` → `1`, `T8–10` → `0`, `≤T7` → hidden
* **Tablets, Keys & Trial items:** Normal/Magic Tablets (`2`), Rare Tablets (`3`), `Pinnacle Keys` (`4`), `Vault Keys` (`3`), `Relics` (`2`), and `Trial Coins` (`2`) are always shown with minimap icons.

### Jewels & Quest Items (`band_rules_jewels_quest.csv`)
* **Time-Lost Jewels:** Matched first at **level `4`** with beam and icon regardless of rarity.
* **Standard Jewels:** `Rare` → `3` (with icon), `Normal`/`Magic` → `2` (starting at band `16–30`).
* **Quest Items:** Matched by whole class at **level `3`** with beam and icon across every band.

### Gems (`band_rules_gems.csv`)
* **Uncut Skill & Spirit Gems:** Each band shows only the **top 2** achievable gem levels (`3` for the highest reachable level in that band, `2` for one level below) and hides all lower levels.
* **Uncut Support Gems:** Each band highlights only the **top** achievable support level (`3`), dropping to minimal **level `0`** from band `76–80` onward once support gems are abundant.
* **Lineage Support Gems:** All named Lineage supports are always shown at **level `4`** across every band.

### Gold (`band_rules_gold.csv`)
* Gold uses minimum `StackSize` thresholds that double through the campaign and stabilize from level `61` onward (`200` → `0`, `400` → `1`, `800` → `2`, `1200` → `3`). Any pile smaller than the band's lowest threshold is hidden. As a deliberate exception to the importance scale, only **level `3`** piles play a sound and show a border.

### Flasks & Charms (`band_rules_flasks.csv`)
* **Life & Mana Flasks:** Only the best bases reachable in the band are shown (`level 0–2`; `Lesser` and `Medium` are always hidden).
* **Charms:** Only `Rare` Charms are shown directly (`level 1`, plus `Unique` via `Unique+`); `Normal`/`Magic` Charms are hidden—and both hidden flasks and hidden charms still pass through the **quality-only Salvage rules** before being hidden.

### Jewellery (`jewellery.csv`)
* Rings, Amulets, and Belts are evaluated by base/implicit category rather than level because useful low-level bases remain relevant at all stages (`Normal`/`Magic` → **level `1`**, `Rare` → **level `2`**).

---

## 5. Equipment Progression in Detail

The `equipment` section covers 22 weapon, offhand, and armour classes (`Bows`, `Crossbows`, `One Hand Maces`, `Two Hand Maces`, `Quarterstaves`, `Spears`, `One Hand Swords`, `Two Hand Swords`, `One Hand Axes`, `Two Hand Axes`, `Sceptres`, `Staves`, `Wands`, `Talismans`, `Foci`, `Quivers`, `Bucklers`, `Shields`, `Body Armours`, `Boots`, `Gloves`, `Helmets`).

### A. Four-Tier Base Progression (Per Attribute Group)
Within each equipment class, bases are tiered separately per attribute group (`STR`, `DEX`, `INT`, `STR/DEX`, `STR/INT`, `DEX/INT`, `STR/DEX/INT`). Small attribute groups with fewer than `4` bases (`min_group_size = 4`) merge into the class's main tiering group so a lone starter or unique hybrid base is not permanently treated as "best", while still keeping its own border colour.

For a band with floor `low` (`band_min`, or `endgame_floor = 75` when `band_min > 75`) and ceiling `high` (`band_max`):

* **Best (`level 3`):** Highest base level `<= high` (all tied bases at that level).
* **Upper Mainstream (`level 2`):** Bases with `midpoint <= level < best`, where `midpoint = (low + best) / 2`.
* **Lower Mainstream (`level 1`):** Bases with `low <= level < midpoint`.
* **Semi-Outdated (`level 0`):** The previous band's best base (highest base level `< low`).
* **Outdated:** Everything older is passed down to the **Salvage** and **Hide** rules.

*(Note: Setting `low = 75` in bands above `75` keeps all top endgame bases visible together instead of hiding `75+` bases as soon as an `81+` base exists.)*

### B. Endgame `ItemLevel` Windows (`76+`)
From band `76–80` onward, `Normal` and `Magic` equipment bases must also satisfy endgame `ItemLevel` breakpoints. The final pre-bonus tier is the **lower** (`min`) of the item's base tier and its `ItemLevel` window tier:

| Band | `ItemLevel` Tier `3` (Best) | `ItemLevel` Tier `2` (Mainstream) | `ItemLevel` Tier `0` (Semi-Outdated) | Below Lowest Window |
|---|---|---|---|---|
| `76–80` | `75–80` | `71–74` | `65–70` | Falls through to Salvage / Hide |
| `81–85` & `86–99` | `82+` | `81` | `75–80` | Falls through to Salvage / Hide |

### C. Implicit Exception List (`config/base_exceptions.csv`)
Some bases stay competitive well above their drop level because of a built-in implicit modifier. Any base matching an exception implicit prefix receives a **`+1` tier bonus** (capped at **level `3`** for `Normal`/`Magic`, and carried into `Rare` scaling up to `4`):

* **Bows** (`+1` additional arrow): *Dualstring Bow*, *Twin Bow*, *Gemini Bow*
* **Crossbows** (`+1` additional ammo): *Dyad Crossbow*, *Twin Crossbow*, *Gemini Crossbow*
* **Spears** (faster bleeding): *Barbed Spear*, *Jagged Spear*, *Spiked Spear*
* **One Hand Maces** (critical multiplier): *Warpick*, *Battle Pick*, *Strife Pick*
* **Quivers** (increased attack speed): *Primed Quiver*
* **Body Armours** (movement speed): *Assassin Garb*, *Falconer's Jacket*, *Corsair Coat*

### D. Rare Item Scaling
* **On a current or semi-outdated base:** `min(capped_base_tier + 1, 4)` (scaling up to **level `4`**).
* **On an outdated base:** **level `0`** in campaign bands (`<= 75`), raised to **level `1`** in `76+` endgame bands.

### E. Salvage Bench Rules (`Normal` / `Magic` Outdated Gear, Flasks & Charms)
Every outdated `Normal` or `Magic` equipment item—and every hidden `Life Flask`, `Mana Flask`, or `Charm` (quality checks only, since they have no sockets)—is evaluated in strict top-down priority against the band's thresholds (`q` / `s`):

* `01–15`: `q = 0`, `s = 0`
* `16–30`: `q = 4`, `s = 0`
* `31–99`: `q = 9`, `s = 1`

**Evaluation order (first match wins):**
1. `Quality >= 13` → **level `3`** (with alert sound)
2. `Quality > q` **and** `Sockets > s` → **level `1`** *(equipment only)*
3. `Quality >= max(7, q + 1)` → **level `1`**
4. `Quality > q` *(only when `q < 7`, i.e., bands `01–30`)* → **level `0`**
5. `Sockets > s` → **level `0`** *(equipment only)*
6. Everything else → **explicit `Hide`**.
