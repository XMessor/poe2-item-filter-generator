---
name: poe2-standard-vs-droplevel-variants
description: Comparison between the standard (BaseType name-list) filters and the _droplevel (DropLevel range) filter variants in XMessor's Simplified Item Filter Generator.
status: production
---

# Standard vs. `_droplevel` Filter Variants

Every build of **XMessor's Simplified Item Filter Generator** produces two parallel sets of `.filter` files:

* **Standard variants:** `v1.0_area_level.filter` and `v1.0_level_01-15.filter` … `v1.0_level_86-99.filter`
* **`_droplevel` variants:** `v1.0_area_level_droplevel.filter` and `v1.0_level_01-15_droplevel.filter` … `v1.0_level_86-99_droplevel.filter`

Both variants do the **exact same thing** on every known item in the game—they differ only in **how the `equipment` section addresses base types**. Running the simulator across the entire RePoE `0.5.5.9` catalog produces **zero differences** between the two variants, and every other section (`unique`, `currency`, `league`, `socketables`, `map_items`, `jewels_quest`, `gems`, `gold`, `flasks`, `jewellery`, `catch_all`) is word-for-word identical in both files.

---

## 1. Standard Variant (Explicit `BaseType` Name Lists)

In the standard files, every equipment rule lists its target base types explicitly by name:

```text
BaseType == "Crude Bow" "Shortbow"
```

* **Advantage:** Very easy to read and inspect directly inside the `.filter` file—you can always see at a glance which exact base types a block matches.

---

## 2. `_droplevel` Variant (`DropLevel` Ranges + Defence Types)

In the `_droplevel` files, explicit base-type name lists are replaced by `DropLevel` range conditions:

```text
DropLevel >= 33
DropLevel <= 51
```

On **armour classes**, the `DropLevel` range is combined with base defence conditions (`BaseArmour`, `BaseEvasion`, `BaseEnergyShield`) to separate the attribute/defence categories—for example, isolating pure Evasion bases:

```text
BaseArmour == 0
BaseEvasion > 0
BaseEnergyShield == 0
DropLevel >= 33
DropLevel <= 51
```

### Bases That Remain Explicitly Named in `_droplevel` Files
Some equipment bases cannot be described purely by a `DropLevel` range and defence type. These stay as explicit `BaseType ==` rules even inside the `_droplevel` files, and **at the same importance level, named rules are always placed before range rules** so they match first:

1. **Exception bases:** Bases that receive a `+1` tier bonus from the implicit exception list (`config/base_exceptions.csv`).
2. **Cross-grouped or custom-bordered bases:** Bases tiered with another group or given a different border colour (for example, attribute groups with fewer than `4` bases that merge into the class's main group for tiering while keeping their own attribute border).
3. **Armour bases with non-standard defences:** Armour pieces whose base defence type (`BaseArmour` / `BaseEvasion` / `BaseEnergyShield`) differs from the rest of their attribute group in that range.
4. **Secondary weapon attribute groups:** Weapons that do not belong to the weapon class's primary attribute group.

---

## 3. Practical Difference: Handling Brand-New, Unknown Bases

The real-world difference between the two variants appears on **patch day or league launch**—when Path of Exile 2 introduces brand-new equipment base types and you have **not yet regenerated** the filter with the updated RePoE catalog:

| Scenario (Before Regenerating for a New Patch) | Standard Variant (`BaseType` Names) | `_droplevel` Variant (`DropLevel` Ranges) |
|---|---|---|
| **A brand-new equipment base drops** | The filter does not recognize its name yet, so an unmatched drop falls through to the **`Catch-all`** safety net (`3i` — visible with warning colours and a red `Cross` minimap icon, but not tiered as equipment). | The filter **automatically tiers the new base** into the matching importance level based on its `DropLevel` (and base defence type on armour). |
| **Trade-off** | Never misclassifies a special base silently—unknown items are flagged visibly by `Catch-all`. | Automatic tiering comes with a trade-off: if the brand-new base should have received an implicit exception bonus, the `_droplevel` filter cannot know that yet and may tier it lower than intended. |

**After regenerating the filter** with the updated RePoE snapshot, both variants once again behave **identically** across every item in the catalog.
