# Notice

Author: Ivan Czar (<https://www.linkedin.com/in/ivan-czar/>)

The [MIT License](LICENSE.md) covers the code, configuration and documentation
written for this project. It does not cover the game data described below.

## Game data: Grinding Gear Games

Path of Exile 2, its item names, item classes and all other game text belong to
[Grinding Gear Games](https://www.grindinggear.com/). This is a free,
non-commercial, fan-made tool. It is not affiliated with, endorsed by or
sponsored by Grinding Gear Games.

The item catalog (`data/catalog_<version>.json`) and the generated `.filter` files contain
item names, item classes, drop levels, level requirements and implicit modifier
identifiers from the game. They are included only because a loot filter cannot
be built without them, and they are meant for personal, non-commercial use, as
the [Path of Exile Terms of Use](https://www.pathofexile.com/legal/terms-of-use-and-privacy-policy)
require. If Grinding Gear Games asks for any of it to be removed, it will be
removed.

## Where the data comes from

- **RePoE, Path of Exile 2 export:** <https://repoe-fork.github.io/poe2/>
  (source: <https://github.com/repoe-fork/repoe>, a fork of
  <https://github.com/brather1ng/RePoE>, built on PyPoE by OmegaK2). The item
  catalog is derived from its `base_items.json` and `item_classes.json`.
  RePoE's code is MIT licensed, Copyright (c) 2016 brather1ng. Its license
  states that the contents of its generated data files belong to Grinding Gear
  Games. This repository therefore does not redistribute RePoE's files: it ships
  a reduced catalog with only the fields the filter engine uses, and the engine
  downloads the full export from RePoE when the maintainer updates it.
- **PoE2DB:** <https://poe2db.tw/>. Used as a reference for the area level of
  each act when the level bands were chosen, and as the base type source of an
  earlier, unpublished prototype.
- **Fextralife Path of Exile 2 Wiki:** the currency list of the same earlier
  prototype.

Thank you to everyone who keeps these projects running: they make community
tools like this one possible.

## Tools

This project was written with the help of AI coding assistants (Claude by
Anthropic, Gemini by Google).
