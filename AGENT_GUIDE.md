# Agent guide

You are an AI agent helping a player build a personal Path of Exile 2 loot filter with this
repository. The player says what matters to them; you turn that into a **profile**, check it,
build it, and hand over the filter. You never need to write code.

Read this whole file before you start. The player-facing documentation is in [`.docs/`](.docs/);
the [Customization Guide](.docs/customization_guide.md) describes every setting in detail.

---

## Ground rules

1. **Write only inside `profiles/<name>/`** (create `profiles/` if it does not exist yet). The
   engine itself appends to `.log/engine.log`; that is expected. Never edit `config/`, `engine/`,
   `data/`, `filter_samples/` or `.docs/`. `config/` holds the defaults and is replaced when the player
   updates the repository; a profile layered on top keeps the player's changes.
2. **Never change the Python code.** If a wish cannot be expressed in a profile (see
   [Not supported](#not-supported)), tell the player and offer the closest supported option.
3. **Show before you write.** Tell the player which file you will create or change and the exact
   lines, and write after they agree.
4. **Validate after every change** (`engine.config`) and build only when it reports 0 errors.
5. **Keep CSV files ASCII-only, without a BOM.** The validator rejects anything else.
6. **Ask one question at a time**, and offer the default as an answer. A player who does not care
   about a setting keeps the default.

## Setup

- Work from the repository root. Python 3.11 or newer is the only requirement (`python --version`;
  on Windows `py` may be the command). No packages, no network access.
- Every command uses `python -E -s -m engine.<module>`: `-E -s` keeps foreign Python settings out
  while the `engine` package still imports from the current folder.
- Profile name: lowercase letters, digits and `_` (e.g. `profiles/ranger_endgame/`). One profile
  per character or playstyle.

---

## Step 1: Interview

Ask these, one at a time. Stop early if the player wants the defaults for the rest.

1. **The character:** class, the weapon classes they use, the armour attributes (STR / DEX / INT).
   Is there a weapon or equipment class they will never use?
2. **Zone level:** do they mostly play zones that match their character level (the normal
   campaign and maps), or do they often farm much lower or higher zones? This decides which file
   to recommend, see [Step 4](#step-4-hand-over).
3. **Strictness:** show more (new player, crafting a lot), default, or stricter (hide more)?
4. **Interests:** crafting and the salvage bench, league mechanics (essences, omens, catalysts,
   liquids), gold, gems. Anything they never pick up?
5. **Look and sound:** label size, sound volume or no sound, colour-blindness or colours they
   dislike, light beams and minimap icons.

Then summarise the wishes in a short list and confirm it with the player before you write.

Not every answer needs a setting. "I use bows and wear DEX armour" changes nothing by itself: the
filter already tiers every equipment class and colours borders by attribute (red STR, green DEX,
blue INT). Keep the defaults for such answers and tell the player so; act only on a wish to show,
hide, emphasise or restyle something.

## Step 2: Turn wishes into settings

The profile folder holds only what changes:

- `structure.toml`: only the keys you change. It is **merged** over `config/structure.toml`:
  tables merge key by key; any other value (a list, a string, a number) replaces the default whole.
- `overrides.csv`: single cells of single items. Start it with the header line of
  `config/overrides.csv`.
- A copy of another config file, only when a recipe below says so. A profile file replaces the
  default file of the same name, and a copy no longer receives updates.

| Wish | Where | How |
|---|---|---|
| Bigger or smaller labels | `structure.toml` | `[importance.0]` … `[importance.5]` `font_size` (defaults 18, 21, 25, 30, 35, 35: levels 4 and 5 share a size, level 5 differs by inverse colours). Never use `32`: a size-32 label means "missed by the filter". |
| Quieter, louder or no sound | `structure.toml` | `[importance.N]` `volume` (whole numbers; defaults 0, 0, 50, 100, 200, 200; `0` = silent). **Every volume you use needs a key in `[icon_size_by_volume]`** (the minimap icon size, `0` largest … `2` smallest), or `engine.config` reports an error. See the example below. |
| Another colour for a kind of item | `structure.toml` | `[categories.<name>]` `text` / `border` as `"R G B A"` (0–255); `icon` must be one of `Red Green Blue Brown White Yellow Cyan Grey Orange Pink Purple`. The category names are in `config/structure.toml`. |
| Other equipment border colours | `structure.toml` | `[attributes.<group>]` `border` / `icon` (`str`, `dex`, `int`, `str_dex`, `str_int`, `dex_int`, `str_dex_int`). |
| Label background | `structure.toml` | `[style]` `default_background`. |
| Stricter or looser salvage | `structure.toml` | `[salvage]` `thresholds` (a list: copy all three entries and change values), `high_quality`, `medium_quality`. |
| Fewer or more rare equipment items | `structure.toml` | `[equipment]` `rare_max_level`, `rare_outdated_campaign`, `rare_outdated_endgame`. |
| Show, hide, raise or lower one item in some bands | `overrides.csv` | One row per item; see [Overrides](#overrides). |
| Hide a whole item class (e.g. "I never use sceptres") | copy of `band_rules_unique.csv` | See [Hide a whole class](#hide-a-whole-class). |
| Other gold thresholds | copy of `band_rules_gold.csv` | The band cells are the minimum `StackSize` per importance level. |

Example, every sound at half volume with the default icon sizes kept:

```toml
# profiles/<name>/structure.toml
[importance.2]
volume = 25
[importance.3]
volume = 50
[importance.4]
volume = 100
[importance.5]
volume = 100

[icon_size_by_volume]   # merged with the defaults (0 = 2, 50 = 2, 100 = 1, 200 = 0)
25 = 2                  # level 2 keeps icon size 2
50 = 1                  # level 3 keeps icon size 1 (overrides the default 50 = 2)
100 = 0                 # levels 4-5 keep icon size 0 (overrides the default 100 = 1)
```

### Band cells

Every rule CSV has one column per band (`1-15`, `16-30`, `31-45`, `46-60`, `61-70`, `71-75`,
`76-80`, `81-85`, `86-99`). A cell is:

| Cell | Meaning |
|---|---|
| `0` … `5` | Shown at importance level 0 (minimal) … 5 (jackpot, inverse colours) |
| `…b` | Adds a light beam, e.g. `3b` |
| `…i` | Adds a minimap icon, e.g. `3i`, `4bi` |
| `H` | Hidden in this band |
| `-` | Cannot drop in this band (the validator checks it against the item catalog) |

### Overrides

Columns (the header of `config/overrides.csv`):

```
section,name,match,item_class,rarity,gem_level,waystone_tier,family,category,1-15,16-30,31-45,46-60,61-70,71-75,76-80,81-85,86-99,note
```

- `section`: the section of the item (`currency`, `league`, `socketables`, `map_items`,
  `jewels_quest`, `gems`, `flasks`, …).
- The key `name,match,item_class,rarity,gem_level,waystone_tier` must match **exactly one** row
  of that section's CSV in `config/`. Copy the values from that row; leave a key column empty
  where that CSV has no such column or the row leaves it empty.
- Fill only the cells you change; an empty cell keeps the default. Put the reason in `note`.

Example, never show Transmutation Shards (row of `config/band_rules_currency.csv`:
`Transmutation Shard,exact,*,…`):

```
currency,Transmutation Shard,exact,*,,,,,,H,H,H,H,H,H,H,H,H,never picked up
```

### Hide a whole class

Copy `config/band_rules_unique.csv` into the profile and add one row per class:

```
*,class,Sceptres,any,3,1,H,H,H,H,H,H,H,H,H,never used
```

The columns: `*` and `class` = the whole class; `Sceptres` = the filter class name; `any` = every
rarity (the unique row above still wins for uniques); `3` = the section's sound family (a hidden
item plays no sound); `1` = drop level (always `1` here); then one `H` per band and a note.
Uniques of a hidden class cannot be hidden this way: if the player asks for that, say it is not
supported.

The unique section is the first in the filter: its `Show` for unique items comes first, then its
`Hide` blocks, before every other section. So unique sceptres still show and all other sceptres
are hidden, **including their salvage (quality or socket) and rare labels**: tell the player. Do **not** put such a row into `band_rules_catch_all.csv`: the catch-all section
shows unmatched items before its own `Hide` blocks, so the class would appear as a red "missed"
label. The exact class names: `python -E -s -m engine.catalog` lists them.

### Not supported

Tell the player plainly when a wish is one of these:

- **Hiding equipment by attribute inside a class** (e.g. "only DEX body armours"). The equipment
  tiers come from an algorithm, not a table. Offer instead: hiding whole classes, or attribute
  border colours that make the wanted bases stand out.
- **Changing the level bands.** Every rule CSV has one column per band, so new bands would need
  new versions of all CSVs. Offer a band file instead (see Step 4).
- **Adding new items by an override.** An override only changes an existing row. A new item that
  the filter misses appears with the red "missed" label; report it to the repository owner.

## Step 3: Validate, build, check

```powershell
python -E -s -m engine.config   --profile profiles/<name>     # must report 0 error(s)
python -E -s -m engine.build    --profile profiles/<name>     # -> profiles/<name>/filters/
python -E -s -m engine.simulate --profile profiles/<name>     # optional, about a minute
```

- **`engine.config` errors** name the file and line: fix the profile and run it again. 18
  warnings about essence cells are normal with the default settings. A warning that a profile file
  "is not used by any section" means a misspelt file name: the build would ignore that file.
- **If the build fails after a clean validation**, the details are in `.log/engine.log` (the
  last traceback). That is a gap in the validator: tell the player and report it to the
  repository owner, then work around it if the log makes the cause clear.
- **`engine.simulate`** lists, per band, the item classes that reach the catch-all, and it must
  end with `0 names/droplevel difference(s)`. The list is long even with the default settings
  (for example legacy classes that never drop in Path of Exile 2, such as Heist, Delve and
  Incubators, and large counts such as Support Gems, Skill Gems or Stackable Currency, which are in
  the default run too). What matters is the **difference** from a run without
  `--profile` (save both outputs and compare them; each run takes about a minute): a class that
  appears only with the profile is something the profile broke.
- **Simulate does not show hidden items, sizes or sounds.** Check those in the built files: search
  `profiles/<name>/filters/v1.0_area_level.filter` for the class or base name (a `Hide` block above
  any `Show` for it), `SetFontSize` and `PlayAlertSound` values.

## Step 4: Hand over

The build writes 20 files into `profiles/<name>/filters/`. Recommend one:

- **`v1.0_area_level.filter`** when the player mostly plays zones that match their character
  level: every band in one file, switching by area level.
- **A band file** (`v1.0_level_XX-YY.filter`) when the player often farms zones far below or
  above their level: its rules apply everywhere, whatever the area level. Choose the band of the
  **zones they farm**, not of the character: from band 76-80 up, normal and magic equipment is
  shown only inside `ItemLevel` windows (`structure.toml` `[equipment] item_level_windows`: item
  level 65+ in band 76-80, 75+ from band 81-85), so the character's band would hide the crafting
  bases that drop in lower zones. Tell the player this trade-off.
- **A `_droplevel` file** after a game patch, before the repository is updated.

[`filter_samples/README.md`](filter_samples/README.md) explains every file. The player copies the
chosen file into `%USERPROFILE%\Documents\My Games\Path of Exile 2\` and selects it under
**Options → Game → Item Filter**. If you run in a cloud sandbox or a chat without access to the
player's computer, offer the chosen `.filter` file (or the whole `filters/` folder as a ZIP) for
download.

Finally, tell the player that their settings are in `profiles/<name>/`: after updating the
repository, the same build command rebuilds their filter with the updates.
