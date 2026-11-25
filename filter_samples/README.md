# Filter samples

Ready-made filters, built from the default settings in [`config/`](../config/). Copy the one
you want into `%USERPROFILE%\Documents\My Games\Path of Exile 2\`, then select it in the game
under **Options → Game → Item Filter**.

Want different colours, sounds, or items shown or hidden? Build your own from a profile: see the
[repository README](../README.md#build-your-own-filter).

## Which file to use

**Not sure? Use `v1.0_area_level.filter`.** It contains every band and switches by the level of
the area you are in, from Act 1 to the endgame.

| File | What it does |
|---|---|
| `v1.0_area_level.filter` | All 9 bands in one file; the active band follows the area level. Set it once and forget it. |
| `v1.0_level_01-15.filter` | Only the rules of band 01–15. |
| `v1.0_level_16-30.filter` | Only the rules of band 16–30. |
| `v1.0_level_31-45.filter` | Only the rules of band 31–45. |
| `v1.0_level_46-60.filter` | Only the rules of band 46–60. |
| `v1.0_level_61-70.filter` | Only the rules of band 61–70. |
| `v1.0_level_71-75.filter` | Only the rules of band 71–75. |
| `v1.0_level_76-80.filter` | Only the rules of band 76–80. |
| `v1.0_level_81-85.filter` | Only the rules of band 81–85. |
| `v1.0_level_86-99.filter` | Only the rules of band 86–99. |
| `*_droplevel.filter` (10 files) | The same 10 filters, but equipment is tiered by `DropLevel` ranges instead of base name lists. |

**When to pick a band file instead of the area-level one:** when your character is well ahead of
or behind the zone level (for example farming low areas with a strong character), or when you want
to switch strictness by hand. A band file applies its rules everywhere, whatever the area level.

**When to pick a `_droplevel` file:** after a game patch adds new bases and before this repository
is updated. Name lists only know the bases that existed at build time; `DropLevel` ranges also
catch new ones. Details: [Standard vs. `_droplevel` variants](../.docs/droplevel_variants.md).

## The bands

| Band | Typical game stage | What changes |
|---|---|---|
| `01–15` | Act 1 | Almost every basic currency, shard and crafting base is useful. |
| `16–30` | Act 2 | Jewels start dropping; the first quality and socket thresholds. |
| `31–45` | Act 3 | Early shards and quality orbs fade; mid-campaign bases rotate in. |
| `46–60` | Act 4 | Waystones (T1) and Greater currencies appear. |
| `61–70` | Early endgame | Gold thresholds stabilise; Perfect Jeweller's Orbs and Tablets appear. |
| `71–75` | Mid endgame | Greater crafting orbs enter; mid-tier Waystones rotate up. |
| `76–80` | High endgame | The endgame base floor and `ItemLevel` windows start; Support Gems drop to minimal. |
| `81–85` | Pinnacle endgame | `ItemLevel` 81 and 82+ windows; T16 Waystones take top priority. |
| `86–99` | Top endgame | The strictest base and `ItemLevel` filtering. |

What the colours, sizes, sounds and minimap icons mean:
[Visual Identity, Colours, Sounds & Minimap Icons](../.docs/visual_and_sound_guide.md). Why an
item is shown or hidden: [Filtering Philosophy](../.docs/filtering_philosophy.md).

The first lines of every file name the filter version and the item data version it was built from.
