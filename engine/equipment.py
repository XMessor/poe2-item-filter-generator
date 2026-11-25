"""Equipment, jewellery and salvage rules (the algorithm sections).

WHAT: Per equipment class and band: base tiers (best / high mainstream / low mainstream /
      half-outdated), the exception bonus, ItemLevel windows in the endgame, rare levels,
      salvage of outdated normal/magic items and an explicit Hide of the remaining known bases.
      Jewellery: borders per base from config/jewellery.csv, fixed levels per rarity.
WHY:  These rules depend on the RePoE catalog (levels, attributes, implicits), so a new 1.0 base
      is tiered without a config change (.docs/filtering_philosophy.md -> 5. Equipment progression in detail).
HOW:  Tier and rare rules name their bases (BaseType ==), so an unknown new base's rare copy
      reaches the catch-all. Salvage and the final Hide are class-wide for normal/magic items
      (user 2026-11-14, file size). Salvage rules are derived from a Hide rule (same conditions +
      Quality/Sockets) and inserted before it - the same mechanism serves the flask section.
"""
from collections import Counter
from dataclasses import dataclass, field, replace

from engine.config import read_csv
from engine.logsetup import get_logger
from engine.rules import Condition, Rule

LOGGER = get_logger("equipment")
RARE = Condition("Rarity", "==", ("Rare",))
NORMAL_MAGIC = Condition("Rarity", "<=", ("Magic",))
NEVER = 99   # sound_from value: no level reaches it
# Base defence condition per attribute letter (format fields; RePoE armour/evasion/energy shield).
DEFENCE_CONDITIONS = (("str", "BaseArmour"), ("dex", "BaseEvasion"), ("int", "BaseEnergyShield"))


# ----------------------------------------------------------------------------------------------
# Bases of one class
# WHAT: level, tiering group, border attribute and exception bonus of every base of a class.
# HOW:  tiering group = own attribute group, unless that group is smaller than min_group_size
#       (or missing) - then the class's main group; the border keeps the own attribute (a base
#       without one, e.g. a starter weapon, takes the main group's colour).
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class EquipBase:
    name: str
    level: int
    tier_group: str
    border_attribute: str | None
    bonus: int
    drop_level: int
    defence_group: str | None


def exception_bonus(base, exceptions):
    """Sum of the +N effects of the exception rows whose implicit prefix the base carries."""
    try:
        return sum(int(row["effect"]) for row in exceptions
                   if row["item_class"] == base.repoe_class
                   and any(implicit.startswith(row["implicit_prefix"]) for implicit in base.implicits))
    except Exception:
        LOGGER.exception("exception_bonus failed: %s", base.name)
        raise


def class_bases(filter_class, catalog, structure, exceptions):
    try:
        bases = [base for base in catalog.bases if base.filter_class == filter_class]
        override = structure.get("class_attribute_override", {}).get(filter_class)
        sizes = Counter(base.attribute_group for base in bases if base.attribute_group)
        minimum = structure["equipment"]["min_group_size"]
        large = [group for group, size in sizes.most_common() if size >= minimum]
        main_group = override or (large[0] if large else (sizes.most_common(1)[0][0] if sizes else "none"))
        result = []
        for base in bases:
            own = override or base.attribute_group
            tier_group = own if own and sizes.get(own, 0) >= minimum else main_group
            result.append(EquipBase(name=base.name, level=base.level_requirement or base.drop_level,
                                    tier_group=override or tier_group, border_attribute=own or main_group,
                                    bonus=exception_bonus(base, exceptions), drop_level=base.drop_level,
                                    defence_group=base.defence_group))
        return result
    except Exception:
        LOGGER.exception("class_bases failed: %s", filter_class)
        raise


# ----------------------------------------------------------------------------------------------
# Tiering
# ----------------------------------------------------------------------------------------------
def classify_band(bases, band, endgame_floor):
    """{name: raw tier} of the current bases of one tiering group (3 best .. 0 half-outdated).

    best = highest level <= band max, and every base above the band; mainstream = band floor <= level < best, split at the
    midpoint (upper half 2, lower half 1); half-outdated = the previous band's best (the highest
    level below the floor). Above the endgame floor the band floor drops to it.
    """
    try:
        low = endgame_floor if band["min"] > endgame_floor else band["min"]
        high = band["max"]
        fitting = [base.level for base in bases if base.level <= high]
        if not fitting:
            return {}
        best = max(fitting)
        midpoint = (low + best) / 2
        older = [base.level for base in bases if base.level < low]
        previous_best = max(older) if older else None
        tiers = {}
        for base in bases:
            if base.level > high or base.level == best:
                # a base above the band counts as best in band (user 2026-11-14, play-test: such
                # bases still drop now and then)
                tiers[base.name] = 3
            elif base.level >= low:
                tiers[base.name] = 2 if base.level >= midpoint else 1
            elif base.level == previous_best:
                tiers[base.name] = 0
        return tiers
    except Exception:
        LOGGER.exception("classify_band failed: band %r", band)
        raise


def current_tiers(bases, band, endgame_floor):
    """{name: raw tier} over all tiering groups of a class."""
    try:
        tiers = {}
        for group in {base.tier_group for base in bases}:
            tiers.update(classify_band([b for b in bases if b.tier_group == group], band, endgame_floor))
        return tiers
    except Exception:
        LOGGER.exception("current_tiers failed: band %r", band)
        raise


def item_level_windows(band, equipment):
    """ItemLevel windows of the band, or None (no ItemLevel rule below the first from_band_min)."""
    try:
        chosen = None
        for entry in sorted(equipment["item_level_windows"], key=lambda e: e["from_band_min"]):
            if band["min"] >= entry["from_band_min"]:
                chosen = entry["windows"]
        return chosen
    except Exception:
        LOGGER.exception("item_level_windows failed: band %r", band)
        raise


# ----------------------------------------------------------------------------------------------
# Rule assembly
# WHAT: merge (name, level, border, extra conditions) entries into ordered rules.
# HOW:  names mode: one BaseType list per group. droplevel mode (the `_droplevel` outputs): a
#       DropLevel range (+ Base* defence conditions on armour) per group instead; bases a range
#       cannot describe stay named - exception bases (bonus), bases tiered or coloured with
#       another group, weapon bases outside the class's main group.
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Target:
    section: str
    band: dict
    filter_class: str
    family: str
    mode: str = "names"                              # "names" or "droplevel"
    bases: dict = field(default_factory=dict)        # name -> EquipBase (droplevel mode)
    range_groups: frozenset = frozenset()            # tier groups a DropLevel range may describe
    defence_mode: bool = False                       # armour: Base* conditions separate the groups


def range_group(target, name):
    """Tier group of a base described by a DropLevel range, or None if it stays named."""
    try:
        if target.mode == "names":
            return None
        base = target.bases[name]
        named = (base.bonus or base.border_attribute != base.tier_group
                 or (target.defence_mode and base.defence_group != base.tier_group)
                 or base.tier_group not in target.range_groups)
        return None if named else base.tier_group
    except Exception:
        LOGGER.exception("range_group failed: %s %r", name, target.filter_class)
        raise


def selector_conditions(target, group, names):
    """BaseType list, or DropLevel range + defence conditions of one merged group."""
    try:
        if group is None:
            return (Condition("BaseType", "==", tuple(sorted(names))),)
        drops = [target.bases[name].drop_level for name in names]
        defence = tuple(Condition(keyword, ">" if letter in group.split("_") else "==", (0,))
                        for letter, keyword in DEFENCE_CONDITIONS) if target.defence_mode else ()
        return defence + (Condition("DropLevel", ">=", (min(drops),)), Condition("DropLevel", "<=", (max(drops),)))
    except Exception:
        LOGGER.exception("selector_conditions failed: %r %r", target.filter_class, group)
        raise


def merged_rules(target, rarity, entries, structure, sound_from):
    """Rules from entries (name, level, border attribute, extra conditions), high level first.

    A rule makes a sound only from level `sound_from` up (user 2026-11-14: equipment sounds only
    for a rare of the best base in the band; normal/magic never)."""
    try:
        groups = {}
        for name, level, attribute, extra in entries:
            groups.setdefault((level, attribute, extra, range_group(target, name)), []).append(name)
        rules = []
        for (level, attribute, extra, group), names in groups.items():
            border = structure["attributes"][attribute]["border"] if attribute else None
            conditions = ((Condition("Class", "==", (target.filter_class,)), rarity)
                          + selector_conditions(target, group, names) + extra)
            rule = Rule(section=target.section, band=target.band, visible=True, conditions=conditions,
                        level=level, family=target.family, border=border, silent=level < sound_from)
            rules.append((group is not None, rule))
        # high level first; at equal level the named rules before the ranges
        return [rule for _ranged, rule in sorted(rules, key=lambda pair: (-pair[1].level, pair[0]))]
    except Exception:
        LOGGER.exception("merged_rules failed: %r", target)
        raise


def rare_entries(bases, tiers, band, equipment):
    try:
        outdated = (equipment["rare_outdated_endgame"] if band["min"] > equipment["endgame_floor"]
                    else equipment["rare_outdated_campaign"])
        entries = []
        for base in bases:
            if base.name in tiers:
                level = min(min(tiers[base.name] + base.bonus, 3) + 1, equipment["rare_max_level"])
            else:
                level = outdated
            entries.append((base.name, level, base.border_attribute, ()))
        return entries
    except Exception:
        LOGGER.exception("rare_entries failed: band %r", band)
        raise


def normal_magic_entries(bases, tiers, band, equipment):
    try:
        windows = item_level_windows(band, equipment)
        entries = []
        for base in bases:
            if base.name not in tiers:
                continue
            if windows is None:
                entries.append((base.name, min(tiers[base.name] + base.bonus, 3), base.border_attribute, ()))
                continue
            for window in windows:
                level = min(min(tiers[base.name], window["tier"]) + base.bonus, 3)
                extra = (Condition("ItemLevel", ">=", (window["min"],)), Condition("ItemLevel", "<=", (window["max"],)))
                entries.append((base.name, level, base.border_attribute, extra))
        return entries
    except Exception:
        LOGGER.exception("normal_magic_entries failed: band %r", band)
        raise


# ----------------------------------------------------------------------------------------------
# Salvage
# WHAT: Show rules for quality/socketed items that a Hide rule would hide; inserted before it.
# ----------------------------------------------------------------------------------------------
def salvage_rules(hide_rule, structure, sockets):
    """Salvage Show rules for the items of one Hide rule (docs: Salvage order, first match wins)."""
    try:
        salvage, band = structure["salvage"], hide_rule.band
        limits = next(t for t in salvage["thresholds"] if band["max"] <= t["up_to"])
        q, s = limits["quality"], limits["sockets"]
        quality_more = Condition("Quality", ">", (q,))
        steps = [(Condition("Quality", ">=", (salvage["high_quality"],)), None, 3, "quality", "2")]
        if sockets:
            steps.append((quality_more, Condition("Sockets", ">", (s,)), 1, "quality_and_socket", None))
        steps.append((Condition("Quality", ">=", (max(salvage["medium_quality"], q + 1),)), None, 1, "quality", None))
        if q < salvage["medium_quality"]:
            steps.append((quality_more, None, 0, "quality", None))
        if sockets:
            steps.append((Condition("Sockets", ">", (s,)), None, 0, "socket", None))
        rules = []
        for first, second, level, colour, family in steps:
            extra = (first,) + ((second,) if second else ())
            rules.append(replace(hide_rule, visible=True, conditions=hide_rule.conditions + extra,
                                 level=level, family=family, border=salvage[colour]))
        return rules
    except Exception:
        LOGGER.exception("salvage_rules failed: %r", hide_rule)
        raise


def with_salvage(rules, structure, sockets):
    """The rules with salvage inserted before every Hide rule."""
    try:
        result = []
        for rule in rules:
            if not rule.visible:
                result += salvage_rules(rule, structure, sockets)
            result.append(rule)
        return result
    except Exception:
        LOGGER.exception("with_salvage failed")
        raise


# ----------------------------------------------------------------------------------------------
# Section entry points
# ----------------------------------------------------------------------------------------------
def class_band_rules(target, bases, structure):
    """Rare, normal/magic, salvage and Hide rules of one class in one band."""
    try:
        equipment, band = structure["equipment"], target.band
        tiers = current_tiers(bases, band, equipment["endgame_floor"])
        rules = merged_rules(target, RARE, rare_entries(bases, tiers, band, equipment), structure,
                             sound_from=equipment["rare_max_level"])
        rules += merged_rules(target, NORMAL_MAGIC, normal_magic_entries(bases, tiers, band, equipment), structure,
                              sound_from=NEVER)
        if any(base.level <= band["max"] for base in bases):
            # class-wide (user 2026-11-14): halves the file size; an unknown new base's normal/magic
            # copy is hidden instead of reaching the catch-all (its rare copy still reaches it)
            hide = Rule(section=target.section, band=band, visible=False,
                        conditions=(Condition("Class", "==", (target.filter_class,)), NORMAL_MAGIC))
            rules += with_salvage([hide], structure, sockets=True)
        return rules
    except Exception:
        LOGGER.exception("class_band_rules failed: %r", target)
        raise


def class_target(section_name, band, filter_class, bases, structure, mode):
    """Target of one class in one band; in droplevel mode with its range settings."""
    try:
        family = structure["equipment"]["family"]
        if mode == "names":
            return Target(section_name, band, filter_class, family)
        defence_mode = any(base.defence_group for base in bases)
        groups = Counter(base.tier_group for base in bases)
        range_groups = frozenset(groups) if defence_mode else frozenset([groups.most_common(1)[0][0]])
        return Target(section_name, band, filter_class, family, mode, {b.name: b for b in bases},
                      range_groups, defence_mode)
    except Exception:
        LOGGER.exception("class_target failed: %s %s", filter_class, mode)
        raise


def build_equipment(section_name, exceptions_path, catalog, structure, mode="names"):
    """All equipment rules, band by band, class by class (structure.toml [equipment] classes)."""
    try:
        exceptions = [row for _line, row in read_csv(exceptions_path)[1]]
        per_class = {name: class_bases(name, catalog, structure, exceptions)
                     for name in structure["equipment"]["classes"]}
        rules = []
        for band in structure["output"]["bands"]:
            for filter_class, bases in per_class.items():
                target = class_target(section_name, band, filter_class, bases, structure, mode)
                rules += class_band_rules(target, bases, structure)
        return rules
    except Exception:
        LOGGER.exception("build_equipment failed")
        raise


def build_jewellery(section_name, path, catalog, structure):
    """Rings, amulets, belts: named rows first, then class rows ('*'); fixed level per rarity."""
    try:
        rows = [row for _line, row in read_csv(path)[1]]
        settings = structure["jewellery"]
        ordered = [row for row in rows if row["name"] != "*"] + [row for row in rows if row["name"] == "*"]
        rules = []
        for band in structure["output"]["bands"]:
            for rarity, level in ((RARE, settings["rare_level"]), (NORMAL_MAGIC, settings["normal_magic_level"])):
                groups = {}
                for row in ordered:
                    key = (catalog.repoe_to_filter[row["item_class"]], row["border"], row["name"] == "*")
                    groups.setdefault(key, []).append(row["name"])
                for (filter_class, border, class_rule), names in groups.items():
                    conditions = (Condition("Class", "==", (filter_class,)), rarity)
                    if not class_rule:
                        conditions += (Condition("BaseType", "==", tuple(names)),)
                    rules.append(Rule(section=section_name, band=band, visible=True, conditions=conditions,
                                      level=level, family=settings["family"], border=border))
        return rules
    except Exception:
        LOGGER.exception("build_jewellery failed: %s", path)
        raise
