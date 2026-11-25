"""Section builders: rule CSVs (+ overrides) -> Rule lists.

WHAT: Turns one band rule CSV into Rules, band by band: rows with the same cell, class, rarity,
      match kind, extra conditions (gem level, waystone tier), family and category merge into
      one rule with a name list. The gold table (cells = minimum stack sizes) has its own builder.
      config/overrides.csv is applied to a section's rows before anything is built.
WHY:  One block per row would make the filter thousands of blocks long; merging keeps it short
      without changing which items match. Overrides keep manual fixes of generated CSVs alive
      across regeneration (user, 2026-11-14).
HOW:  Inside a band: visible rules first, higher level first (stable, so CSV order breaks
      ties), then the Hide rules (explicit Hide for every H cell - the catch-all at the end of
      the filter must only see unmatched items). Rows of one section must therefore not
      overlap at different levels; where they do, the higher level wins.
"""
from engine.config import OVERRIDE_KEY, band_columns, read_csv, row_key
from engine.logsetup import get_logger
from engine.rules import Condition, Rule, parse_cell

LOGGER = get_logger("sections")
# Filter syntax of the CSV column values (format fields, .docs/customization_guide.md -> 2.).
RARITY_CONDITIONS = {
    "any": None,
    "unique": Condition("Rarity", "==", ("Unique",)),
    "rare": Condition("Rarity", "==", ("Rare",)),
    "normal_magic": Condition("Rarity", "<=", ("Magic",)),
}
EXTRA_CONDITION_COLUMNS = {"gem_level": "GemLevel", "waystone_tier": "WaystoneTier"}


# ----------------------------------------------------------------------------------------------
# Rows and overrides
# WHAT: reading a section's rows and applying config/overrides.csv to them.
# HOW:  an override row names an existing row by OVERRIDE_KEY; its non-empty cells replace the
#       generated ones. config.check_overrides guarantees that every override hits one row.
# ----------------------------------------------------------------------------------------------
def load_rows(path, section_name, overrides):
    """(header, rows) of a section CSV with its overrides applied."""
    try:
        header, rows, findings = read_csv(path)
        if findings:
            raise ValueError(f"{path.name}: encoding findings {findings} - run engine.config first")
        index = {row_key(row): row for _line, row in rows}
        for _line, override in overrides:
            if override["section"] != section_name:
                continue
            target = index[row_key({key: override.get(key, "") for key in OVERRIDE_KEY})]
            for column in header:
                if column in override and override[column] and column not in OVERRIDE_KEY:
                    target[column] = override[column]
        return header, rows
    except Exception:
        LOGGER.exception("load_rows failed: %s section %s", path, section_name)
        raise


def resolve_category(row, structure):
    """Row category, else the family default; None for '-' or no category."""
    try:
        category = row.get("category") or ""
        if category == "-":
            return None
        if category:
            return category
        return structure["families"].get(row.get("family"), {}).get("category")
    except Exception:
        LOGGER.exception("resolve_category failed: %r", row)
        raise


def extra_conditions(row):
    """GemLevel / WaystoneTier conditions of a row (empty cell = no condition)."""
    try:
        return tuple(Condition(keyword, "==", (int(row[column]),))
                     for column, keyword in EXTRA_CONDITION_COLUMNS.items() if row.get(column))
    except Exception:
        LOGGER.exception("extra_conditions failed: %r", row)
        raise


def group_key(row, spec, structure):
    """Rows with equal keys merge; Hide rules ignore style, so they merge more widely."""
    try:
        base = (row.get("match"), row.get("item_class", "*"), row.get("rarity", "any"),
                extra_conditions(row), spec)
        if not spec.visible:
            return base + (None, None)
        family = None if row.get("family") == "-" else row.get("family")
        return base + (family, resolve_category(row, structure))
    except Exception:
        LOGGER.exception("group_key failed: %r", row)
        raise


def conditions_for(match, item_class, rarity, names):
    """Class / Rarity / BaseType conditions of one merged group."""
    try:
        conditions = []
        if item_class and item_class != "*":
            conditions.append(Condition("Class", "==", (item_class,)))
        if RARITY_CONDITIONS[rarity]:
            conditions.append(RARITY_CONDITIONS[rarity])
        if match == "exact":
            conditions.append(Condition("BaseType", "==", tuple(names)))
        elif match == "contains":
            conditions.append(Condition("BaseType", "", tuple(names)))
        return tuple(conditions)
    except Exception:
        LOGGER.exception("conditions_for failed: %r %r %r", match, item_class, rarity)
        raise


# ----------------------------------------------------------------------------------------------
# Band tables
# ----------------------------------------------------------------------------------------------
def band_rules(section_name, band, column, rows, structure):
    """Merged, ordered rules of one band."""
    try:
        groups = {}
        for _line, row in rows:
            spec = parse_cell(row[column])
            if spec is None:
                continue
            groups.setdefault(group_key(row, spec, structure), []).append(row["name"])
        rules = []
        for (match, item_class, rarity, extra, spec, family, category), names in groups.items():
            rules.append(Rule(section=section_name, band=band, visible=spec.visible,
                              conditions=conditions_for(match, item_class, rarity, names) + extra,
                              level=spec.level, beam=spec.beam, icon=spec.icon,
                              family=family, category=category))
        shown = sorted((r for r in rules if r.visible), key=lambda r: -r.level)
        return shown + [r for r in rules if not r.visible]
    except Exception:
        LOGGER.exception("band_rules failed: %s band %r", section_name, band)
        raise


# ----------------------------------------------------------------------------------------------
# Gold table
# WHAT: one row per importance level, cells = minimum StackSize; sound/border per row.
# HOW:  rows are emitted high level first; stacks below the lowest threshold get a Hide.
# ----------------------------------------------------------------------------------------------
def gold_rules(section_name, band, column, rows, structure):
    try:
        rules, lowest = [], None
        for _line, row in sorted(rows, key=lambda pair: -int(pair[1]["level"])):
            if row[column] == "-":
                continue
            threshold = int(row[column])
            lowest = threshold if lowest is None else min(lowest, threshold)
            conditions = conditions_for(row["match"], row.get("item_class", "*"), row.get("rarity", "any"), [row["name"]])
            if threshold > 0:
                conditions += (Condition("StackSize", ">=", (threshold,)),)
            rules.append(Rule(section=section_name, band=band, visible=True, conditions=conditions,
                              level=int(row["level"]), family=row["family"],
                              category=resolve_category(row, structure),
                              silent=row["sound"] == "no", hide_border=row["border"] == "no"))
        if lowest:
            names = sorted({row["name"] for _line, row in rows})
            rules.append(Rule(section=section_name, band=band, visible=False,
                              conditions=conditions_for("exact", "*", "any", names)))
        return rules
    except Exception:
        LOGGER.exception("gold_rules failed: %s band %r", section_name, band)
        raise


# ----------------------------------------------------------------------------------------------
# Entry points
# ----------------------------------------------------------------------------------------------
def build_band_table(section_name, path, bands, structure, overrides=()):
    """All rules of one band table (generic or gold kind), band by band."""
    try:
        header, rows = load_rows(path, section_name, overrides)
        builder = gold_rules if "level" in header else band_rules
        rules = []
        for band, column in zip(bands, band_columns(header)):
            rules += builder(section_name, band, column, rows, structure)
        return rules
    except Exception:
        LOGGER.exception("build_band_table failed: %s", path)
        raise
