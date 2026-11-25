# XMessor's Simplified Item Filter Generator

A rule-driven loot filter generator for **Path of Exile 2**, with ready-to-use `.filter` files.

Every filter follows one strict hierarchy, **Good Find → Salvage → Hide**: valuable drops and
relevant crafting bases stand out at once, outdated bases with quality or sockets are marked for
the salvage bench, and everything else is hidden.

You can use it in three ways:

1. **Use a ready-made filter.** Copy a file from [`filter_samples/`](filter_samples/) into your
   game folder; its README tells you which file does what.
2. **Make it yours by talking to an AI agent.** Tell your coding agent what matters to you
   ("I play a Ranger, I never use maces or sceptres, hide runes after level 60, and make the
   sounds quieter"). It writes your settings into a profile, checks them and builds your filter. See [`AGENT_GUIDE.md`](AGENT_GUIDE.md).
3. **Make it yours by hand.** Edit a few CSV or TOML values in your own profile and run one
   command. See the [Customization Guide](.docs/customization_guide.md).

---

## Preface

The core idea is an **adaptive approach to item progression**. What matters on the ground in
Path of Exile 2 is never static: in the opening acts almost every basic currency orb, low-level
uncut gem, early crafting base and any item with a point of quality or a socket is worth picking
up. Further into the campaign and the endgame, yesterday's upgrades turn into clutter, salvage
thresholds tighten, and your attention moves to top-tier bases, `ItemLevel` breakpoints and
high-end crafting materials.

So the generator writes both a **zone-adaptive filter** (`v1.0_area_level.filter`), which
changes with the level of the area you are in, and **fixed level-band filters** (`01-15` to
`86-99`) for when your character is ahead of or behind the zone level.

### The code is verbose

I wrote my first lines of code when the year still started with a `1` and Turbo Pascal was a thing. I am not a professional
software engineer: after my university programming exams I turned to physics instead. That is why
the code here is **intentionally verbose and explicit**: every step is written out, so that
anyone reading it (my future self included) can see *what* it does and *why*.

---

## Filter variants

Every build writes 20 files across **9 level bands** (`01-15`, `16-30`, `31-45`, `46-60`,
`61-70`, `71-75`, `76-80`, `81-85`, `86-99`):

| File | How it works | Best for |
|---|---|---|
| `v1.0_area_level.filter` | One file; the bands switch by the zone's `AreaLevel` | "Set and forget" from Act 1 to the endgame |
| `v1.0_level_01-15.filter` … `v1.0_level_86-99.filter` | One file per band | A character level far from the zone level, or switching bands by hand |
| `*_droplevel.filter` | The same, but equipment is tiered by `DropLevel` instead of base name lists | A fallback when a patch adds bases before the filter is updated |

More: [Standard vs. `_droplevel` variants](.docs/droplevel_variants.md).

## Install a filter (Windows)

1. Copy the `.filter` file into `%USERPROFILE%\Documents\My Games\Path of Exile 2\`.
2. In the game, open **Options → Game → Item Filter**, select the file and click **Save**.

---

## Build your own filter

**Requirements:** Python 3.11 or newer. Nothing else: no packages, no internet connection.
Everything the build needs, including the item catalog, is in this repository.

Your settings live in a **profile**: a folder under `profiles/` that holds only the files and
values you changed. Everything you do not change comes from `config/`, so when this repository
is updated you get the fixes without losing your settings.

```powershell
# from the repository root
python -E -s -m engine.config --profile profiles/my_profile          # check the settings
python -E -s -m engine.build  --profile profiles/my_profile          # -> profiles/my_profile/filters/
```

The [Customization Guide](.docs/customization_guide.md) explains every setting.

### With an AI agent

Any coding agent that can read files and run commands works: Claude Code, Gemini CLI, Codex,
Cursor and others. Open the repository in it and start with *"Read AGENT_GUIDE.md and help me
build my filter."* The agent follows [`AGENT_GUIDE.md`](AGENT_GUIDE.md): it asks about your build
and your priorities, writes your profile, validates it and builds the filter.

You do not need to install anything locally either:

- **Claude Code on the web** can work on the repository in the cloud (fork it to your account).
- **A Claude chat with code execution** works too: download this repository as a ZIP, upload it,
  and start with *"Read AGENT_GUIDE.md and help me build my filter."* Download the `.filter` file it
  produces.

---

## Documentation

- [Filtering Philosophy & Item Progression](.docs/filtering_philosophy.md)
- [Visual Identity, Colours, Sounds & Minimap Icons](.docs/visual_and_sound_guide.md)
- [Standard vs. `_droplevel` Filter Variants](.docs/droplevel_variants.md)
- [Customization Guide](.docs/customization_guide.md)
- [Developer & Architecture Guide](.docs/developer_guide.md)

## Status and maintenance

This is a hobby project, provided as it is. I update it when I find something to fix while
playing, and when a game patch changes the item data.

## License and credits

The code is released under the [MIT License](LICENSE.md). Path of Exile 2 and its game data
belong to Grinding Gear Games. This project is not affiliated with or endorsed by them. Item data
comes from the RePoE project. Full credits and sources: [NOTICE.md](NOTICE.md).
