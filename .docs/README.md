---
name: poe2-filter-documentation-index
description: Index of the English documentation of XMessor's Simplified Item Filter Generator (Path of Exile 2, v1.0). The overview, preface and installation live in the repository root README.md.
status: production
---

# Documentation

The overview, the preface and the installation steps are in the [repository README](../README.md).

* **[Filtering Philosophy & Item Progression](filtering_philosophy.md)** — How the `Survive → Salvage → Hide` hierarchy works, the 12 evaluation sections, the 9 level bands, equipment base tiering by attribute group, endgame `ItemLevel` windows, implicit exceptions, and salvage rules.
* **[Standard vs. `_droplevel` Filter Variants](droplevel_variants.md)** — How the explicit `BaseType` name-list filters and the `DropLevel` range variants work, which bases stay named, and how each variant handles brand-new patch items before a catalog update.
* **[Visual Identity, Colours, Sounds & Minimap Icons](visual_and_sound_guide.md)** — In-game reference for the `0–5` importance scale, why font size `32` is reserved as an "unfiltered item" indicator, the 16 sound families, attribute border colours (`STR`/`DEX`/`INT`), and minimap icon shapes.
* **[Customization Guide](customization_guide.md)** — How to make a profile (`profiles/<name>/`), override single items in its `overrides.csv`, change per-band tables and `structure.toml` values, and rebuild your filters.
* **[Developer & Architecture Guide](developer_guide.md)** — Tech stack, the RePoE data source and the reduced item catalog, the profile layer, and a file-by-file guide to `engine/`, `engine/rulegen/` and `config/`.
