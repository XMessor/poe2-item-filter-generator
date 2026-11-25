"""Simulator: runs catalog items through the built rules, without the game.

WHAT: For every band, sample items are made from the catalog bases (rarity, quality, sockets,
      item level variants) and matched against the rule list the renderer writes. Reports
      (1) which classes reach the catch-all and (2) where the names and the droplevel builds
      give a different result for the same item.
WHY:  The quality gate before an in-game test: a missed class or a wrong DropLevel range shows
      up here at once (engine/README.md, module 7).
HOW:  First matching rule wins, as in the game. Conditions are evaluated with the filter
      semantics the engine uses (==, >=, <=, >, BaseType substring without operator). The item
      model only carries what the conditions need; Base* values are 1/0 from the defence group.
      Conditions the model cannot answer (GemLevel, StackSize, WaystoneTier) count as met, so the
      first rule of such a group decides - enough to tell whether a section covers the item.
      Rules are pre-filtered by their Class condition for speed.
      Usage: python -E -s -m engine.simulate [--repoe-version 0.5.5.9] [--config config] [--profile DIR]
"""
import argparse
import sys
from dataclasses import dataclass

from engine.build import build_sections
from engine.catalog import load_catalog, resolve_version
from engine.logsetup import get_logger
from engine.profile import load_config

LOGGER = get_logger("simulate")
RARITY_ORDER = {"Normal": 0, "Magic": 1, "Rare": 2, "Unique": 3}
DEFENCE_LETTERS = {"BaseArmour": "str", "BaseEvasion": "dex", "BaseEnergyShield": "int"}


@dataclass(frozen=True)
class SampleItem:
    filter_class: str
    base_type: str
    rarity: str
    drop_level: int
    item_level: int
    quality: int
    sockets: int
    defence_group: str | None


# ----------------------------------------------------------------------------------------------
# Matching
# ----------------------------------------------------------------------------------------------
def numeric_value(item, keyword, band):
    try:
        if keyword in DEFENCE_LETTERS:
            return 1 if item.defence_group and DEFENCE_LETTERS[keyword] in item.defence_group.split("_") else 0
        values = {"DropLevel": item.drop_level, "ItemLevel": item.item_level, "Quality": item.quality,
                  "Sockets": item.sockets, "AreaLevel": band["min"]}
        return values.get(keyword)
    except Exception:
        LOGGER.exception("numeric_value failed: %s %r", keyword, item)
        raise


def condition_holds(condition, item, band):
    """True/False; a condition the item model cannot answer (StackSize, GemLevel ...) is met."""
    try:
        keyword, operator, values = condition.keyword, condition.operator, condition.values
        if keyword == "Class":
            return item.filter_class in values
        if keyword == "BaseType":
            return item.base_type in values if operator == "==" else any(v in item.base_type for v in values)
        if keyword == "Rarity":
            actual, limit = RARITY_ORDER[item.rarity], RARITY_ORDER[values[0]]
            return actual == limit if operator == "==" else actual <= limit
        actual = numeric_value(item, keyword, band)
        if actual is None:
            return True
        limit = values[0]
        return {"==": actual == limit, ">=": actual >= limit, "<=": actual <= limit, ">": actual > limit}[operator]
    except Exception:
        LOGGER.exception("condition_holds failed: %r %r", condition, item)
        raise


def first_match(rules, item, band):
    """The first rule whose conditions all hold, or None."""
    try:
        for rule in rules:
            if all(condition_holds(condition, item, band) for condition in rule.conditions):
                return rule
        return None
    except Exception:
        LOGGER.exception("first_match failed: %r", item)
        raise


def outcome(rule):
    """What the player sees, comparable between builds."""
    try:
        if rule is None:
            return ("no rule",)
        return (rule.section, rule.visible, rule.level, rule.border, rule.family, rule.beam, rule.icon)
    except Exception:
        LOGGER.exception("outcome failed: %r", rule)
        raise


# ----------------------------------------------------------------------------------------------
# Samples
# ----------------------------------------------------------------------------------------------
def samples(catalog, band):
    """Item variants per base; equipment-like variants for every class (cheap and uniform)."""
    try:
        levels = sorted({band["max"], band["min"], 65, 71, 75, 81, 82}) if band["min"] > 75 else [band["max"]]
        items = []
        for base in catalog.bases:
            if base.drop_level > band["max"]:
                continue
            for rarity in ("Normal", "Rare"):
                for item_level in levels:
                    for quality, sockets in ((0, 0), (5, 0), (10, 0), (15, 0), (0, 2), (10, 2)):
                        items.append(SampleItem(base.filter_class, base.name, rarity, base.drop_level,
                                                item_level, quality, sockets, base.defence_group))
        return items
    except Exception:
        LOGGER.exception("samples failed: band %r", band)
        raise


def rules_by_class(built, band):
    """{filter class or None: rules} - None holds the rules without a Class condition."""
    try:
        index = {}
        for _name, rules in built:
            for rule in rules:
                if rule.band != band:
                    continue
                classes = next((c.values for c in rule.conditions if c.keyword == "Class"), (None,))
                for filter_class in classes:
                    index.setdefault(filter_class, []).append(rule)
        return index
    except Exception:
        LOGGER.exception("rules_by_class failed: band %r", band)
        raise


def class_rules(index, built, band, filter_class, cache):
    """Rules that can match an item of this class, in filter order."""
    try:
        if filter_class not in cache:
            wanted = set(map(id, index.get(filter_class, []) + index.get(None, [])))
            cache[filter_class] = [r for _n, rules in built for r in rules if r.band == band and id(r) in wanted]
        return cache[filter_class]
    except Exception:
        LOGGER.exception("class_rules failed: %s", filter_class)
        raise


def band_report(built_names, built_drop, catalog, band):
    """({class: set of catch-all base types}, list of names/droplevel differences) for one band."""
    try:
        names_index, drop_index = rules_by_class(built_names, band), rules_by_class(built_drop, band)
        names_cache, drop_cache = {}, {}
        catch_all, differences = {}, []
        for item in samples(catalog, band):
            names_rules = class_rules(names_index, built_names, band, item.filter_class, names_cache)
            drop_rules = class_rules(drop_index, built_drop, band, item.filter_class, drop_cache)
            names_rule = first_match(names_rules, item, band)
            if names_rule is not None and names_rule.section == "catch_all":
                catch_all.setdefault(item.filter_class, set()).add(item.base_type)
            drop_outcome = outcome(first_match(drop_rules, item, band))
            if outcome(names_rule) != drop_outcome:
                differences.append((item, outcome(names_rule), drop_outcome))
        return catch_all, differences
    except Exception:
        LOGGER.exception("band_report failed: band %r", band)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repoe-version", default=None, help="default: structure.toml [repoe] version")
    parser.add_argument("--config", default="config")
    parser.add_argument("--profile", default=None, help="player profile folder layered over --config")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--show", type=int, default=5, help="differences printed per band")
    parser.add_argument("--dry-run", action="store_true", help="read-only module: same as a normal run")
    args = parser.parse_args()
    try:
        config_dir, structure = load_config(args.config, args.profile)
        catalog = load_catalog(args.project_root, structure["repoe"],
                               resolve_version(args.repoe_version, structure["repoe"]))
        built_names, _skipped = build_sections(structure, config_dir, catalog, set(), "names")
        built_drop, _skipped = build_sections(structure, config_dir, catalog, set(), "droplevel")
        total = 0
        for band in structure["output"]["bands"]:
            catch_all, differences = band_report(built_names, built_drop, catalog, band)
            total += len(differences)
            ranked = sorted(catch_all.items(), key=lambda pair: -len(pair[1]))
            classes = ", ".join(f"{name} {len(bases)}" for name, bases in ranked)
            print(f"\033[93m{band['min']}-{band['max']}\033[0m catch-all: {classes or '-'}; names/droplevel differences: {len(differences)}")
            for item, names_outcome, drop_outcome in differences[:args.show]:
                print(f"    {item.filter_class} {item.base_type!r} {item.rarity} ilvl {item.item_level} q{item.quality} s{item.sockets}: names {names_outcome} / droplevel {drop_outcome}")
        colour = "\033[92m" if total == 0 else "\033[91m"
        print(f"{colour}{total} names/droplevel difference(s).\033[0m")
        sys.exit(1 if total else 0)
    except SystemExit:
        raise
    except Exception as error:
        LOGGER.exception("simulate CLI failed: %r", vars(args))
        print(f"\033[91mSimulation failed: {error} (details: .log/engine.log)\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
