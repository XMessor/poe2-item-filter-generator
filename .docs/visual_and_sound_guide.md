---
name: poe2-visual-and-sound-guide
description: Visual identity, importance scale, 16 sound families, RGB colour categories, black label background, equipment attribute borders, jewellery borders, salvage colours, and minimap icon shapes for XMessor's Simplified Item Filter Generator (PoE2 v1.0).
status: production
---

# Visual Identity, Colours, Sounds & Minimap Icons

Every visible drop in **XMessor's Simplified Item Filter Generator** (`v1.0`) communicates three questions at a glance—even before you hover over the label:

1. **How important is it?** → Driven by the **Importance Scale (`0–5`)** (font size, alert volume, and level `5` inverse highlight).
2. **What kind of item dropped?** → Driven by the **Sound Family (`1–16`)** (alert sound ID and minimap icon shape).
3. **What exact category or stat group is it?** → Driven by **RGB Colour Categories** (text, border, light beam, and equipment/jewellery border rules).

---

## 1. Layered Visual & Audio Architecture

When `engine/render.py` writes a `Show` block from `config/structure.toml`, each property comes from its own independent layer:

| Layer | What Determines It |
|---|---|
| **Visibility (`Show` / `Hide`)** | Progression rules (`Survive → Salvage → Hide`) |
| **Font Size & Sound Volume** | **Importance Level** (`0–5`) |
| **Sound ID & Minimap Icon Shape** | **Sound Family** (`1–16`) |
| **Text Colour & Named Beam/Icon Colour** | **Colour Category** (defaults per family, overridable per item) |
| **Background Colour** | Black `0 0 0 235` (`[style] default_background`) on every visible label |
| **Border Colour** | Category border (currency/gems/league), attribute requirement (`STR`/`DEX`/`INT` on equipment), implicit/base (`config/jewellery.csv`), or salvage tier |
| **Inverse Highlight** | Level `5` only (swaps background to full text colour and text to opaque black) |
| **Minimap Icon Size** | Derived from **Alert Volume** |

---

## 2. The Importance Scale (`H`, `0–5`)

| Level | Meaning | Font Size | Alert Volume | Visual / Audio Behaviour |
|---|---|---|---|---|
| `H` | Hidden | — | — | Emitted as an explicit `Hide` block inside its section. |
| `0` | Minimal / Pickup | `18` | `0` (silent) | Low-priority pickups (e.g., older flasks, outdated campaign rares, low salvage). |
| `1` | Basic | `21` | `0` (silent) | Standard visible drops, lower mainstream gear, and non-rare jewellery. |
| `2` | Good | `25` | `50` | Solid drops (upper mainstream bases, mid-tier currency, rare jewellery). |
| `3` | Valuable | `30` | `100` | Best-in-band gear bases, chaos-tier currency, rare jewels, top Waystones, and `Quality >= 13` salvage. |
| `4` | Very Valuable | `35` | `200` | Uniques, Time-Lost jewels, Lineage supports, pinnacle keys, and high-tier collectibles. |
| `5` | Jackpot / Chase | `35` | `200` | **Inverse style:** bright category colour becomes the background (`255` alpha) with black text (`0 0 0 255`). |

### Why Font Size `32` Is Never Used
Path of Exile 2 renders unfiltered items at default font size **`32`**. The importance scale deliberately skips `32` (jumping from `30` to `35`). If you ever see a label at default size `32` on the ground, you immediately know the item was missed even by the `Catch-all` safety net—or that the filter is not loaded properly.

*(Exception: `Gold` level `2` disables its sound and border even at font size `25`, and `Gold` levels `0–2` omit borders so gold piles never clutter the screen.)*

---

## 3. Sound Families (`1–16`) & Minimap Icon Shapes

Every item belongs to one **Sound Family**. The **Sound ID** tells your ears *what* dropped, while the **Minimap Icon Shape** tells your eyes the exact same category on the map. Sound plays only on importance levels `2–5` (unless a rule is marked silent).

| Sound ID | Family Name | Minimap Icon Shape | What Drops Here |
|---|---|---|---|
| `1` | Especially valuable & rare | `Star` | Divine Orb, Fracturing Orb, Mirror of Kalandra, Hinekora's Lock, Orb of Annulment, Starlit Ore |
| `2` | Good base (& high salvage) | `Kite` | Equipment bases, jewellery, and `Quality >= 13` salvage |
| `3` | Unique & rarer | `Pentagon` | All `Unique` items across every class |
| `4` | Chaos tier | `Diamond` | Chaos Orb, Exalted Orb, Vaal Orb, Exceptional Verisium |
| `5` | Jeweller's & Desecrated bones | `Diamond` | Jeweller's Orbs and Desecrated bones |
| `6` | Map & endgame items | `Square` | Waystones, Tablets, Pinnacle Keys, Vault Keys, Relics, Trial Coins |
| `7` | Catch-all (& Gold) | `Cross` | Unmatched safety-net items (Gold also uses ID `7` on level `3` piles) |
| `8` | Collectibles | `Triangle` | Essences, Catalysts, Delirium Liquids, Expedition Artifacts/Coinage, Splinters, Keys |
| `9` | Omens | `Moon` | All Omens |
| `10` | Quality improvers | `Diamond` | Blacksmith's Whetstone, Armourer's Scrap, Arcanist's Etcher, Glassblower's Bauble, Gemcutter's Prism |
| `11` | Jewels & Quest items | `Hexagon` | Time-Lost Jewels, standard Jewels, Quest Items |
| `12` | Flasks & Charms | `Raindrop` | Life Flasks, Mana Flasks, Charms |
| `13` | Socketables | `UpsideDownHouse` | Runes, Soul Cores, Idols, and named `@65` socketables |
| `14` | Crafting | `Diamond` | Transmutation, Augmentation, Alchemy, Chance, Regal, Shards, Artificer's, Verisium/Alloy/Crest |
| `15` | Gems | `Circle` | Uncut Skill, Spirit, and Support Gems |
| `16` | Lineage support gems | `Circle` | Named Lineage Support Gems |

### Minimap Icon Size (By Volume)
Whenever a rule enables a minimap icon (`i` in CSV), its size maps directly from alert volume (`[icon_size_by_volume]` in `config/structure.toml`):

* Volume `200` (levels `4–5`) → **`0`** *(largest icon)*
* Volume `100` (level `3`) → **`1`** *(medium icon)*
* Volume `50` or `0` (levels `0–2`) → **`2`** *(smallest icon)*

---

## 4. Colour Categories, Tinted Backgrounds & Light Beams

* **Black background (`[style] default_background = "0 0 0 235"`):** Every visible label uses the same black background; the earlier 10% text-colour tint was dropped after play-testing (2026-11-14). Categories without a custom text colour keep the game's default rarity text colour.
* **Light Beams (`b` in CSV):** Emits a permanent `PlayEffect <NamedColour>` beam (without `Temp`) matching the category's named `icon` colour. Used selectively for rare/notable drops (`Greater`/`Perfect` currency, `Unique+`, `Divine`/`Fracturing`/`Mirror`, `Time-Lost` jewels, Quest items, `@65` named socketables).

| Category | Text RGB | Border RGB | Named Icon / Beam Colour | Notes |
|---|---|---|---|---|
| `exotic` (Family `1`) | `255 0 255 255` | `255 0 255 255` | `Purple` | Distinct from pink league items so top drops stand out on the minimap. |
| `unique` (Family `3`) | `255 128 64 255` | `255 128 64 255` | `Orange` | Classic unique orange + `Pentagon` icon. |
| `chaos_tier` (Family `4`) | `0 255 0 255` | `0 255 0 255` | `Green` | Chaos, Exalted, Vaal, Exceptional Verisium. |
| `collectibles` (Family `8`) | `255 0 150 255` | `255 0 150 255` | `Pink` | Distinguished from Families `5` & `9` by `Triangle` shape. |
| `jewellers_bones` (Family `5`) | `255 150 200 255` | `255 150 200 255` | `Pink` | Distinguished by `Diamond` shape. |
| `omens` (Family `9`) | `200 100 255 255` | `200 100 255 255` | `Pink` | Distinguished by `Moon` shape. |
| `map_items` (Family `6`) | `100 75 50 255` | `150 100 75 255` border, `50 25 0 235` background | `Brown` | Waystones, Tablets, Keys, Relics, Trial Coins (border and background from user 2026-11-15, text colour unchanged). Waystone level 3 (`3i`): font `30`, sound `6` / `100`, `Brown Square` icon. |
| `catch_all` (Family `7`) | `255 0 0 255` | `255 255 0 255` | `Red` | High-contrast warning red text with yellow border. |
| `quality_improvers` (Family `10`) | `200 200 0 255` | `200 200 0 255` | `Yellow` | Whetstone, Scrap, Etcher, Bauble, Gemcutter's. |
| `jewels_quest` (Family `11`) | `150 255 0 255` | `0 255 0 255` | `Green` | Lime-green text + green border. |
| `life_flask` (Family `12`) | *(game default)* | `255 60 60 255` | `Red` | Red border + `Raindrop`. |
| `mana_flask` (Family `12`) | *(game default)* | `60 100 255 255` | `Blue` | Blue border + `Raindrop`. |
| `charm` (Family `12`) | *(game default)* | `155 155 155 255` | `Grey` | Grey border + `Raindrop`. |
| `socketable` (Family `13`) | *(game default)* | `255 255 255 255` | `White` | White border + `UpsideDownHouse`. |
| `crafting_magic` (Family `14`) | `136 136 255 255` | `136 136 255 255` | `Blue` | Transmutation, Augmentation. |
| `crafting_rare` (Family `14`) | `255 220 0 255` | `255 220 0 255` | `Yellow` | Alchemy, Chance, Regal. |
| `crafting_forging` (Family `14`) | `160 180 200 255` | `160 180 200 255` | `Grey` | Artificer's Orb & Shard. |
| `crafting_verisium` (Family `14`) | `0 255 255 255` | `0 255 255 255` | `Cyan` | Verisium, Alloy, Crest. |
| `gems` (Family `15`) | `27 162 155 255` | `27 162 155 255` | `Cyan` | Uncut Skill, Spirit, and Support Gems. |
| `lineage` (Family `16`) | `100 150 250 255` | `100 150 250 255` | `Blue` | Named Lineage Support Gems. |
| `gold` (Family `7`) | *(game default)* | `255 215 0 255` | `Yellow` | Gold border applied on level `3` stacks only. |

---

## 5. Equipment, Salvage & Jewellery Borders

Equipment and jewellery keep the game's default rarity text colour (`Normal`, `Magic`, `Rare`) on a dark `0 0 0 235` background so you always see item rarity immediately, while the **border colour** reveals the item's attribute requirement, salvage reason, or implicit type.

### Equipment Attribute Borders
Driven by each base's RePoE attribute requirements (with `Quivers` assigned `dex` so they stay paired with `Bows`):

| Attribute Requirement | Border RGB | Colour |
|---|---|---|
| `STR` | `255 0 0 255` | Red |
| `DEX` (incl. `Quivers`) | `0 255 0 255` | Green |
| `INT` | `0 0 255 255` | Blue |
| `STR + DEX` | `255 255 0 255` | Yellow |
| `STR + INT` | `255 0 255 255` | Purple |
| `DEX + INT` | `0 255 255 255` | Cyan |
| `STR + DEX + INT` | `255 255 255 255` | White |

### Salvage Borders (`[salvage]` in `config/structure.toml`)
Outdated `Normal`/`Magic` gear (and quality-salvageable flasks/charms) replace the attribute border with a **salvage border** so you instantly know *why* a low base was shown:

| Salvage Trigger | Border RGB | Colour |
|---|---|---|
| **Quality** (`Q >= 13`, `Q >= max(7, q+1)`, or `Q > q`) | `255 150 255 255` | Bright Pink *(level `3` on `Q >= 13` also plays sound ID `2`)* |
| **Quality + Sockets** (`Q > q` and `S > s`) | `200 150 255 255` | Lavender |
| **Sockets only** (`S > s`) | `150 150 150 255` | Grey |

### Jewellery Implicit Borders (`config/jewellery.csv`)
Rings and Amulets are bordered by their implicit bonus rather than level, while all **Belts** share a uniform grey class border:

| Border Colour | RGB | Jewellery Bases |
|---|---|---|
| **Red** | `255 0 0 255` | *Iron*, *Ruby*, *Kinetic*, *Vitalic* Rings; *Crimson*, *Amber*, *Bloodstone* Amulets |
| **Green** | `0 255 0 255` | *Emerald* Ring; *Jade* Amulet |
| **Blue** | `0 0 255 255` | *Lazuli*, *Sapphire*, *Pearl*, *Mnemonic* Rings; *Azure*, *Lapis*, *Lunar* Amulets |
| **Yellow** | `255 255 0 255` | *Topaz* Ring |
| **Purple** | `255 0 255 255` | *Amethyst*, *Prismatic*, *Two-Stone*, *Biostatic*, *Abyssal Signet*, *Oneiric* Rings; *Pearlescent* Amulet |
| **White** | `255 255 255 255` | *Stellar*, *Solar*, *Veridical Chain* Amulets |
| **Orange** | `255 150 0 255` | Rarity & socket implicits (*Gold Ring*, *Gold Amulet*, *Unset*, *Breach*, *Refined Breach*, *Grasping* Rings; *Corona* Amulet) |
| **Grey** | `155 155 155 255` | `PrefixSuffixAllowed` bases (*Dusk*, *Gloam*, *Penumbra*, *Tenebrous*, *Distorted*, *Twisted*, *Lament*, *Portent*, *Absent*) and all **Belts** |
