"""RePoE diff: what changed between two snapshots, and where the new items land.

WHAT: Compares two catalogs class by class (added, removed, changed bases; new and vanished
      classes) and runs every added base through the current rules: an added base that reaches
      the catch-all needs a decision (a rule, an override, or nothing).
WHY:  The decision list of the `update poe2` skill - what a new game version brought and what
      the filter does not handle yet.
HOW:  A base is identified by (filter class, name). Changed = drop level, level requirement,
      attribute group, defence group or implicits differ. Coverage uses engine.simulate on the
      NEW catalog with the current config (run engine/rulegen/regen_all.py first), in the first
      band the base can drop in, as a normal and as a rare item.
      --config-before DIR adds the rows of the rule CSVs that regeneration changed (a copy of
      config/ taken before engine/rulegen/regen_all.py ran).
      Usage: python -E -s -m engine.diff --old-version 0.5.5.9 --new-version 1.0.0.0 [--report FILE]
             [--config-before DIR]
"""
import argparse
import sys
from pathlib import Path

from engine.build import build_sections
from engine.catalog import load_catalog
from engine.logsetup import get_logger
from engine.profile import load_config
from engine.simulate import SampleItem, first_match

LOGGER = get_logger("diff")
COMPARED_FIELDS = ("drop_level", "level_requirement", "attribute_group", "defence_group", "implicits")


# ----------------------------------------------------------------------------------------------
# Catalog comparison
# ----------------------------------------------------------------------------------------------
def compare(old, new):
    """{"added": [base], "removed": [base], "changed": [(old, new, fields)], classes added/removed}."""
    try:
        old_index = {(b.filter_class, b.name): b for b in old.bases}
        new_index = {(b.filter_class, b.name): b for b in new.bases}
        changed = []
        for key in sorted(old_index.keys() & new_index.keys()):
            fields = [f for f in COMPARED_FIELDS if getattr(old_index[key], f) != getattr(new_index[key], f)]
            if fields:
                changed.append((old_index[key], new_index[key], fields))
        old_classes = {b.filter_class for b in old.bases}
        new_classes = {b.filter_class for b in new.bases}
        return {
            "added": [new_index[k] for k in sorted(new_index.keys() - old_index.keys())],
            "removed": [old_index[k] for k in sorted(old_index.keys() - new_index.keys())],
            "changed": changed,
            "classes_added": sorted(new_classes - old_classes),
            "classes_removed": sorted(old_classes - new_classes),
        }
    except Exception:
        LOGGER.exception("compare failed: %s -> %s", old.version, new.version)
        raise


def coverage(added, built, bands):
    """[(base, band, normal section, rare section)] of the added bases under the current rules."""
    try:
        result = []
        for base in added:
            band = next((b for b in bands if base.drop_level <= b["max"]), bands[-1])
            rules = [rule for _name, section_rules in built for rule in section_rules if rule.band == band]
            sections = []
            for rarity in ("Normal", "Rare"):
                item = SampleItem(base.filter_class, base.name, rarity, base.drop_level, band["max"], 0, 0,
                                  base.defence_group)
                rule = first_match(rules, item, band)
                sections.append(rule.section if rule else "no rule")
            result.append((base, band, sections[0], sections[1]))
        return result
    except Exception:
        LOGGER.exception("coverage failed")
        raise


def csv_row_changes(before_dir, after_dir):
    """{file: (removed rows, added rows)} of the CSVs that differ between two config folders."""
    try:
        changes = {}
        for after in sorted(Path(after_dir).glob("*.csv")):
            before = Path(before_dir) / after.name
            old_rows = before.read_text(encoding="utf-8").splitlines() if before.exists() else []
            new_rows = after.read_text(encoding="utf-8").splitlines()
            old_set, new_set = set(old_rows), set(new_rows)
            removed = [row for row in old_rows if row not in new_set]
            added = [row for row in new_rows if row not in old_set]
            if removed or added:
                changes[after.name] = (removed, added)
        return changes
    except Exception:
        LOGGER.exception("csv_row_changes failed: %s -> %s", before_dir, after_dir)
        raise


# ----------------------------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------------------------
def report_lines(old, new, changes, covered, csv_changes=None):
    """Markdown report for the maintainer."""
    try:
        lines = [f"# RePoE changes: {old.version} → {new.version}", "",
                 f"- added bases: {len(changes['added'])}, removed: {len(changes['removed'])}, "
                 f"changed: {len(changes['changed'])}",
                 f"- added classes: {', '.join(changes['classes_added']) or '–'}",
                 f"- removed classes: {', '.join(changes['classes_removed']) or '–'}", ""]
        needs = [c for c in covered if "catch_all" in (c[2], c[3])]
        lines += ["## Needs a decision: added bases that reach the catch-all", ""]
        lines += [f"- {base.filter_class} · {base.name} (@{base.drop_level}, band {band['min']}–{band['max']}): "
                  f"normal → {normal}, rare → {rare}" for base, band, normal, rare in needs] or ["- none"]
        lines += ["", "## Added bases and their section", ""]
        lines += [f"- {base.filter_class} · {base.name} (@{base.drop_level}): normal → {normal}, rare → {rare}"
                  for base, _band, normal, rare in covered] or ["- none"]
        lines += ["", "## Removed bases", ""]
        lines += [f"- {base.filter_class} · {base.name}" for base in changes["removed"]] or ["- none"]
        lines += ["", "## Changed bases", ""]
        lines += [f"- {o.filter_class} · {o.name}: " + "; ".join(f"{f} {getattr(o, f)!r} → {getattr(n, f)!r}" for f in fields)
                  for o, n, fields in changes["changed"]] or ["- none"]
        if csv_changes is not None:
            lines += ["", "## Rule CSV changes (after regeneration)", ""]
            if not csv_changes:
                lines.append("- none")
            for file, (removed, added) in csv_changes.items():
                lines.append(f"### {file}: -{len(removed)} / +{len(added)} rows")
                lines += [f"    - {row}" for row in removed] + [f"    + {row}" for row in added]
        return lines + [""]
    except Exception:
        LOGGER.exception("report_lines failed")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--old-version", required=True)
    parser.add_argument("--new-version", required=True)
    parser.add_argument("--config", default="config")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--report", default=None, help="markdown file to write (default: print only)")
    parser.add_argument("--config-before", default=None, help="copy of config/ before regeneration")
    parser.add_argument("--dry-run", action="store_true", help="compute and print, write no report")
    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # the report uses non-ASCII text
        config_dir, structure = load_config(args.config)
        old =load_catalog(args.project_root, structure["repoe"], args.old_version)
        new = load_catalog(args.project_root, structure["repoe"], args.new_version)
        changes = compare(old, new)
        built, _skipped = build_sections(structure, config_dir, new, set(), "names")
        covered = coverage(changes["added"], built, structure["output"]["bands"])
        needs = sum(1 for c in covered if "catch_all" in (c[2], c[3]))
        print(f"{old.version} -> {new.version}: added {len(changes['added'])}, removed {len(changes['removed'])}, "
              f"changed {len(changes['changed'])}, new classes {len(changes['classes_added'])}; "
              f"\033[93m{needs} added base(s) reach the catch-all\033[0m")
        csv_changes = csv_row_changes(args.config_before, args.config) if args.config_before else None
        text = "\n".join(report_lines(old, new, changes, covered, csv_changes))
        if args.report and not args.dry_run:
            Path(args.report).write_text(text, encoding="utf-8", newline="\n")
            print(f"\033[92mReport written: {args.report}\033[0m")
        elif not args.report:
            print(text)
    except Exception as error:
        LOGGER.exception("diff CLI failed: %r", vars(args))
        print(f"\033[91mDiff failed: {error} (details: .log/engine.log)\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
