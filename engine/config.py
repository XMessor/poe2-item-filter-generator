"""Config loader and validator of the v1.0 engine.

WHAT: Loads config/structure.toml and every CSV it refers to, and checks them against the format
      (.docs/customization_guide.md -> 2.) and against the RePoE catalog: file encoding, band headers, cell
      syntax, match/rarity/family/class values, names that must exist in RePoE, "-" cells that
      contradict the drop level, duplicate rows, rows shadowed by an earlier section, and the
      structure settings (colours, icon names, section sources).
WHY:  A typo in a hand-edited CSV must fail loudly before a filter is built, and a RePoE update
      must show at once which configured names no longer exist.
HOW:  Each check returns a list of Finding records (error or warning); nothing is changed.
      Exit code 1 if any error. Read-only, so --dry-run is a no-op.
      With --profile DIR the layered config is checked (engine/profile.py), plus a warning for
      every profile file that no setting refers to (a misspelt name would otherwise be ignored).
      Usage: python -E -s -m engine.config [--repoe-version 0.5.5.9] [--config config] [--profile DIR]
"""
import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from engine.catalog import load_catalog, resolve_version
from engine.logsetup import get_logger
from engine.profile import STRUCTURE_FILE, load_config

LOGGER = get_logger("config")

# Format fields of the rule CSVs (.docs/customization_guide.md -> 2.) and game protocol values.
KNOWN_COLUMNS = {"name", "match", "item_class", "rarity", "family", "category", "drop_level", "gem_level",
                 "waystone_tier", "level", "sound", "border", "note", "section"}
# Identity of a rule row; an override row names its target by these columns.
OVERRIDE_KEY = ("name", "match", "item_class", "rarity", "gem_level", "waystone_tier")
MATCH_VALUES = {"exact", "contains", "class"}
RARITY_VALUES = {"any", "normal_magic", "rare", "unique"}
YES_NO = {"yes", "no"}
BAND_HEADER = re.compile(r"^(\d+)-(\d+)$")
CELL_PATTERN = re.compile(r"^(H|-|[0-5]b?i?)$")
COLOUR_PATTERN = re.compile(r"^\d{1,3} \d{1,3} \d{1,3} \d{1,3}$")
NAMED_COLOURS = {"Red", "Green", "Blue", "Brown", "White", "Yellow", "Cyan", "Grey", "Orange",
                 "Pink", "Purple"}
ICON_SHAPES = {"Circle", "Diamond", "Hexagon", "Square", "Star", "Triangle", "Cross", "Moon",
               "Raindrop", "Kite", "Pentagon", "UpsideDownHouse"}


# ----------------------------------------------------------------------------------------------
# Records
# WHAT: a finding, and the context one table check needs (keeps signatures short).
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Finding:
    level: str          # "error" or "warning"
    file: str
    line: int           # 0 = whole file
    message: str


@dataclass
class TableContext:
    file: str
    bands: list
    structure: dict
    catalog: object


# ----------------------------------------------------------------------------------------------
# Reading
# WHAT: CSV reading with the encoding rules (ASCII only, no BOM - Excel on Windows).
# ----------------------------------------------------------------------------------------------
def read_csv(path):
    """(header, [(line number, row dict)], findings) of one CSV file."""
    try:
        raw = Path(path).read_bytes()
        findings = []
        if raw.startswith(b"\xef\xbb\xbf"):
            findings.append(Finding("error", path.name, 0, "BOM at file start"))
        for number, line in enumerate(raw.splitlines(), start=1):
            if any(byte > 127 for byte in line):
                findings.append(Finding("error", path.name, number, "non-ASCII character"))
        reader = csv.DictReader(raw.decode("utf-8-sig", errors="replace").splitlines())
        rows = [(number, row) for number, row in enumerate(reader, start=2)]
        return reader.fieldnames or [], rows, findings
    except Exception:
        LOGGER.exception("read_csv failed: %s", path)
        raise


def band_columns(header):
    """Band column names of a header, in file order."""
    try:
        return [column for column in header if BAND_HEADER.match(column)]
    except Exception:
        LOGGER.exception("band_columns failed: %r", header)
        raise


# ----------------------------------------------------------------------------------------------
# Band rule tables
# WHAT: header, per-row value checks, cell syntax, name existence, drop-level consistency.
# HOW:  a table with a `level` column is the gold kind: its cells are minimum stack sizes.
# ----------------------------------------------------------------------------------------------
def check_header(ctx, header):
    try:
        findings = []
        expected = [f"{band['min']}-{band['max']}" for band in ctx.bands]
        if band_columns(header) != expected:
            findings.append(Finding("error", ctx.file, 1, f"band columns {band_columns(header)} != {expected}"))
        for column in header:
            if column not in KNOWN_COLUMNS and not BAND_HEADER.match(column):
                findings.append(Finding("error", ctx.file, 1, f"unknown column {column!r}"))
        for column in ("name", "match", "family"):
            if column not in header:
                findings.append(Finding("error", ctx.file, 1, f"missing column {column!r}"))
        return findings
    except Exception:
        LOGGER.exception("check_header failed: %s", ctx.file)
        raise


def check_values(ctx, line, row):
    """match, rarity, family, item_class, sound/border values of one row."""
    try:
        findings = []
        families = set(ctx.structure["families"])
        known_classes = set(ctx.catalog.repoe_to_filter.values()) | {"*"}

        def bad(message):
            try:
                findings.append(Finding("error", ctx.file, line, message))
            except Exception:
                LOGGER.exception("bad failed: %s:%s %r", ctx.file, line, message)
                raise

        if row.get("match") not in MATCH_VALUES:
            bad(f"match {row.get('match')!r} not in {sorted(MATCH_VALUES)}")
        if row.get("match") == "class" and row.get("name") != "*":
            bad("a class rule must have name '*'")
        if "rarity" in row and row["rarity"] not in RARITY_VALUES:
            bad(f"rarity {row['rarity']!r} not in {sorted(RARITY_VALUES)}")
        if row.get("family") not in families | {"-"}:
            bad(f"family {row.get('family')!r} not defined in structure.toml")
        if "item_class" in row and row["item_class"] not in known_classes:
            bad(f"item_class {row['item_class']!r} is not a filter class in RePoE {ctx.catalog.version}")
        for column in ("sound", "border"):
            if column in row and row[column] not in YES_NO:
                bad(f"{column} {row[column]!r} must be yes or no")
        category = row.get("category") or ""
        if category and category != "-" and category not in ctx.structure["categories"]:
            bad(f"category {category!r} not defined in structure.toml")
        family_default = ctx.structure["families"].get(row.get("family"), {}).get("category")
        if not category and row.get("family") != "-" and not family_default:
            bad(f"family {row.get('family')!r} has no default category: the row must name one")
        return findings
    except Exception:
        LOGGER.exception("check_values failed: %s line %d", ctx.file, line)
        raise


def check_cells(ctx, line, row, header):
    """Cell syntax; a sounding level (2+) needs a family."""
    try:
        findings = []
        stack_size_cells = "level" in header
        for column in band_columns(header):
            cell = row.get(column) or ""
            if stack_size_cells:
                if not (cell == "-" or cell.isdigit()):
                    findings.append(Finding("error", ctx.file, line, f"{column}: {cell!r} is not a stack size"))
                continue
            if not CELL_PATTERN.match(cell):
                findings.append(Finding("error", ctx.file, line, f"{column}: bad cell {cell!r}"))
            elif cell[0].isdigit() and int(cell[0]) >= 2 and row.get("family") == "-":
                findings.append(Finding("error", ctx.file, line, f"{column}: level {cell[0]} sounds but family is '-'"))
        return findings
    except Exception:
        LOGGER.exception("check_cells failed: %s line %d", ctx.file, line)
        raise


def matching_bases(ctx, row):
    """Catalog bases a row refers to (empty for class rules and unknown names)."""
    try:
        item_class = row.get("item_class")
        restrict = item_class if item_class and item_class != "*" else None
        name, match = row.get("name", ""), row.get("match")
        bases = [base for base in ctx.catalog.bases if restrict is None or base.filter_class == restrict]
        if match == "exact":
            return [base for base in bases if base.name == name]
        if match == "contains":
            return [base for base in bases if name in base.name]
        return []
    except Exception:
        LOGGER.exception("matching_bases failed: %s %r", ctx.file, row.get("name"))
        raise


def check_name(ctx, line, row):
    """exact/contains names must exist in the catalog (within the row's class if given)."""
    try:
        if row.get("match") not in ("exact", "contains") or matching_bases(ctx, row):
            return []
        where = f" in class {row['item_class']!r}" if row.get("item_class") not in (None, "*") else ""
        return [Finding("error", ctx.file, line,
                        f"{row['match']} name {row['name']!r} not found{where} in RePoE {ctx.catalog.version}")]
    except Exception:
        LOGGER.exception("check_name failed: %s line %d", ctx.file, line)
        raise


def check_drop_level(ctx, line, row, header):
    """drop_level vs RePoE, and '-' cells in bands where RePoE says the item can drop.

    '-' writes no rule, so such an item would reach the catch-all if it drops there. Tiered rows
    (essences, runes by prefix) do this on purpose, so it is one warning per row, not an error.
    A level cell before the drop level is harmless (the rule never fires) and is not reported.
    """
    try:
        if "drop_level" not in row or not row["drop_level"].isdigit():
            return []
        findings, drop = [], int(row["drop_level"])
        bases = matching_bases(ctx, row)
        if bases and min(base.drop_level for base in bases) != drop:
            findings.append(Finding("warning", ctx.file, line,
                                    f"drop_level {drop} but RePoE says {min(b.drop_level for b in bases)}"))
        droppable_dash = [column for band, column in zip(ctx.bands, band_columns(header))
                          if row.get(column) == "-" and drop <= band["max"]]
        if droppable_dash:
            findings.append(Finding("warning", ctx.file, line,
                                    f"{row['name']!r}: '-' in {', '.join(droppable_dash)} although drop_level is {drop} (would reach the catch-all)"))
        return findings
    except Exception:
        LOGGER.exception("check_drop_level failed: %s line %d", ctx.file, line)
        raise


def row_key(row):
    """Identity of a row; two rows with the same key in one file are a duplicate."""
    try:
        return tuple(row.get(column, "") or "" for column in OVERRIDE_KEY + ("level",))
    except Exception:
        LOGGER.exception("row_key failed: %r", row)
        raise


def check_band_table(ctx, path):
    """All checks of one band rule CSV; returns (findings, rows)."""
    try:
        header, rows, findings = read_csv(path)
        findings += check_header(ctx, header)
        seen = {}
        for line, row in rows:
            findings += check_values(ctx, line, row)
            findings += check_cells(ctx, line, row, header)
            findings += check_name(ctx, line, row)
            findings += check_drop_level(ctx, line, row, header)
            key = row_key(row)
            if key in seen:
                findings.append(Finding("error", ctx.file, line, f"duplicate of line {seen[key]}"))
            seen.setdefault(key, line)
        return findings, rows
    except Exception:
        LOGGER.exception("check_band_table failed: %s", path)
        raise


def check_shadowing(tables):
    """Warn when an exact name of a later section is already taken by an earlier section."""
    try:
        findings, owner = [], {}
        for file, rows in tables:
            for line, row in rows:
                if row.get("match") != "exact":
                    continue
                key = (row["name"], row.get("item_class", "*"), row.get("rarity", "any"))
                if key in owner and owner[key][0] != file:
                    findings.append(Finding("warning", file, line,
                                            f"{row['name']!r} already matched by {owner[key][0]} line {owner[key][1]} (earlier section wins)"))
                owner.setdefault(key, (file, line))
        return findings
    except Exception:
        LOGGER.exception("check_shadowing failed")
        raise


# ----------------------------------------------------------------------------------------------
# Equipment tables and structure
# WHAT: base_exceptions.csv and jewellery.csv (RePoE class ids), and structure.toml settings.
# ----------------------------------------------------------------------------------------------
def check_base_exceptions(path, catalog):
    try:
        header, rows, findings = read_csv(path)
        for line, row in rows:
            implicits = {implicit for base in catalog.bases if base.repoe_class == row["item_class"]
                         for implicit in base.implicits}
            if not implicits:
                findings.append(Finding("error", path.name, line, f"RePoE class {row['item_class']!r} has no bases"))
            elif not any(implicit.startswith(row["implicit_prefix"]) for implicit in implicits):
                findings.append(Finding("error", path.name, line,
                                        f"no {row['item_class']} base has an implicit {row['implicit_prefix']}*"))
            if not re.match(r"^\+\d+$", row.get("effect", "")):
                findings.append(Finding("error", path.name, line, f"effect {row.get('effect')!r} is not +N"))
        return findings
    except Exception:
        LOGGER.exception("check_base_exceptions failed: %s", path)
        raise


def check_jewellery(path, catalog):
    try:
        header, rows, findings = read_csv(path)
        for line, row in rows:
            if row["name"] != "*" and row["name"] not in catalog.names(repoe_class=row["item_class"]):
                findings.append(Finding("error", path.name, line,
                                        f"{row['name']!r} not found in RePoE class {row['item_class']!r}"))
            if not COLOUR_PATTERN.match(row.get("border", "")):
                findings.append(Finding("error", path.name, line, f"border {row.get('border')!r} is not 'R G B A'"))
            if row.get("icon") not in NAMED_COLOURS:
                findings.append(Finding("error", path.name, line, f"icon {row.get('icon')!r} is not a named colour"))
        return findings
    except Exception:
        LOGGER.exception("check_jewellery failed: %s", path)
        raise


def check_overrides(path, structure, config_dir):
    """Every override row must hit exactly one row of its section; its cells must be valid."""
    try:
        header, rows, findings = read_csv(path)
        sources = {s["name"]: s["source"] for s in structure["output"]["sections"]
                   if s["source"].startswith("band_rules_")}
        tables = {}
        for line, row in rows:
            source = sources.get(row.get("section"))
            if not source:
                findings.append(Finding("error", path.name, line, f"section {row.get('section')!r} has no rule CSV"))
                continue
            if source not in tables:
                tables[source] = [r for _l, r in read_csv(config_dir / source)[1]]
            key = row_key({column: row.get(column, "") for column in OVERRIDE_KEY})
            hits = sum(1 for target in tables[source] if row_key(target) == key)
            if hits != 1:
                findings.append(Finding("error", path.name, line, f"key {key[:6]} hits {hits} rows of {source} (must be 1)"))
            for column in band_columns(header):
                if row.get(column) and not CELL_PATTERN.match(row[column]):
                    findings.append(Finding("error", path.name, line, f"{column}: bad cell {row[column]!r}"))
            if row.get("family") and row["family"] not in structure["families"]:
                findings.append(Finding("error", path.name, line, f"family {row['family']!r} undefined"))
            if row.get("category") and row["category"] not in set(structure["categories"]) | {"-"}:
                findings.append(Finding("error", path.name, line, f"category {row['category']!r} undefined"))
        return findings
    except Exception:
        LOGGER.exception("check_overrides failed: %s", path)
        raise


def check_style_table(file, section, entries):
    """Colour strings and named colours/shapes of one structure.toml table."""
    try:
        findings = []
        for key, entry in entries.items():
            for field in ("text", "border", "background"):
                if field in entry and not COLOUR_PATTERN.match(entry[field]):
                    findings.append(Finding("error", file, 0, f"[{section}.{key}] {field} {entry[field]!r} is not 'R G B A'"))
            if "icon" in entry and entry["icon"] not in NAMED_COLOURS:
                findings.append(Finding("error", file, 0, f"[{section}.{key}] icon {entry['icon']!r} is not a named colour"))
            if "icon_shape" in entry and entry["icon_shape"] not in ICON_SHAPES:
                findings.append(Finding("error", file, 0, f"[{section}.{key}] icon_shape {entry['icon_shape']!r} unknown"))
        return findings
    except Exception:
        LOGGER.exception("check_style_table failed: %s", section)
        raise


def check_structure(structure, config_dir, catalog):
    try:
        file, findings = "structure.toml", []
        for section in ("families", "categories", "attributes"):
            findings += check_style_table(file, section, structure.get(section, {}))
        for number, family in structure.get("families", {}).items():
            if family.get("category") and family["category"] not in structure.get("categories", {}):
                findings.append(Finding("error", file, 0, f"[families.{number}] category {family['category']!r} undefined"))
        missing_levels = [level for level in map(str, range(6)) if level not in structure.get("importance", {})]
        if missing_levels:
            findings.append(Finding("error", file, 0, f"importance levels missing: {missing_levels}"))
        # The minimap icon size is looked up by alert volume (render.style_lines), so every volume
        # in use needs a key - found by an agent test on 2026-11-25: a halved volume crashed the build.
        icon_sizes = structure.get("icon_size_by_volume", {})
        for level, importance in sorted(structure.get("importance", {}).items()):
            if str(importance.get("volume")) not in icon_sizes:
                findings.append(Finding("error", file, 0, f"[importance.{level}] volume {importance.get('volume')!r} "
                                        f"has no [icon_size_by_volume] key (icon size 0, 1 or 2)"))
        filter_classes = set(catalog.repoe_to_filter.values())
        for name in structure["salvage"].get("extra_classes", []) + list(structure.get("class_attribute_override", {})):
            if name not in filter_classes:
                findings.append(Finding("error", file, 0, f"{name!r} is not a filter class"))
        for section in structure["output"]["sections"]:
            for source in [section["source"]] + section.get("extra", []):
                if source != "algorithm" and not (config_dir / source).exists():
                    findings.append(Finding("error", file, 0, f"section {section['name']!r}: {source} missing"))
        return findings
    except Exception:
        LOGGER.exception("check_structure failed: %s", config_dir)
        raise


def check_profile_files(structure, config_dir):
    """Warning for each profile file that no setting refers to: the build would ignore it."""
    try:
        used = {STRUCTURE_FILE, structure["overrides"]["file"]}
        for section in structure["output"]["sections"]:
            used.update([section["source"]] + section.get("extra", []))
        return [Finding("warning", name, 0, "profile file is not used by any section - misspelt name?")
                for name in config_dir.profile_files() if name not in used]
    except Exception:
        LOGGER.exception("check_profile_files failed: %s", config_dir)
        raise


# ----------------------------------------------------------------------------------------------
# Orchestration and CLI
# ----------------------------------------------------------------------------------------------
def validate(config_dir, structure, catalog):
    """All findings of the layered config (engine/profile.ConfigLayers), in section order."""
    try:
        findings = check_structure(structure, config_dir, catalog) + check_profile_files(structure, config_dir)
        bands, tables = structure["output"]["bands"], []
        for section in structure["output"]["sections"]:
            sources = [section["source"]] + section.get("extra", [])
            for source in sources:
                path = config_dir / source
                if source == "algorithm" or not path.exists():
                    continue
                if source == "base_exceptions.csv":
                    findings += check_base_exceptions(path, catalog)
                elif source == "jewellery.csv":
                    findings += check_jewellery(path, catalog)
                else:
                    table_findings, rows = check_band_table(TableContext(source, bands, structure, catalog), path)
                    findings += table_findings
                    tables.append((source, rows))
        overrides = config_dir / structure["overrides"]["file"]
        if overrides.exists():
            findings += check_overrides(overrides, structure, config_dir)
        return findings + check_shadowing(tables)
    except Exception:
        LOGGER.exception("validate failed: %s", config_dir)
        raise


def print_report(findings):
    """Grouped report; returns the error count."""
    try:
        colours = {"error": "\033[91m", "warning": "\033[93m"}
        for finding in sorted(findings, key=lambda f: (f.file, f.line, f.level)):
            where = f"{finding.file}:{finding.line}" if finding.line else finding.file
            print(f"{colours[finding.level]}{finding.level:7}\033[0m {where}  {finding.message}")
        errors = sum(1 for f in findings if f.level == "error")
        warnings = len(findings) - errors
        colour = "\033[91m" if errors else "\033[92m"
        print(f"{colour}{errors} error(s), {warnings} warning(s).\033[0m")
        return errors
    except Exception:
        LOGGER.exception("print_report failed")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repoe-version", default=None, help="default: structure.toml [repoe] version")
    parser.add_argument("--config", default="config")
    parser.add_argument("--profile", default=None, help="player profile folder layered over --config")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--dry-run", action="store_true", help="read-only module: same as a normal run")
    args = parser.parse_args()
    try:
        config_dir, structure = load_config(args.config, args.profile)
        catalog = load_catalog(args.project_root, structure["repoe"],
                               resolve_version(args.repoe_version, structure["repoe"]))
        errors = print_report(validate(config_dir, structure, catalog))
        sys.exit(1 if errors else 0)
    except SystemExit:
        raise
    except Exception as error:
        LOGGER.exception("config CLI failed: %r", vars(args))
        print(f"\033[91mConfig check failed: {error} (details: .log/engine.log)\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
