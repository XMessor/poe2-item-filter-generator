"""Intermediate rule model of the engine.

WHAT: Condition and Rule records, and the parser of one band cell ("3bi", "H", "-").
WHY:  Sections produce rules, the renderer turns rules into filter text. With this model in
      between, a section never writes filter syntax and the renderer never reads a CSV - so the
      two outputs (per band, AreaLevel) and later the simulator share one source.
HOW:  A Rule is one future Show/Hide block: its conditions, its band, and either a hidden flag
      or an importance level with beam/icon flags, a sound family and a colour category.
"""
import re
from dataclasses import dataclass

from engine.logsetup import get_logger

LOGGER = get_logger("rules")
CELL_PATTERN = re.compile(r"^([0-5])(b?)(i?)$")      # cell notation, .docs/customization_guide.md -> 2.


@dataclass(frozen=True)
class Condition:
    keyword: str        # filter condition keyword, e.g. "BaseType", "Class", "Rarity"
    operator: str       # "==", ">=", "<=" or "" (substring match for BaseType)
    values: tuple       # rendered as given; strings are quoted by the renderer


@dataclass(frozen=True)
class CellSpec:
    visible: bool
    level: int | None
    beam: bool
    icon: bool


@dataclass(frozen=True)
class Rule:
    section: str
    band: dict                  # {"min": .., "max": ..}
    visible: bool
    conditions: tuple           # of Condition
    level: int | None = None
    beam: bool = False
    icon: bool = False
    family: str | None = None   # sound family / icon shape; None = silent, no icon shape
    category: str | None = None # colour category; None = no colours of its own
    silent: bool = False        # no sound although the level would sound (gold exception)
    hide_border: bool = False   # no border although the category has one (gold exception)
    border: str | None = None   # explicit border RGBA (equipment: attribute or salvage colour)


def parse_cell(cell):
    """CellSpec of one cell; None for '-' (cannot drop: no rule at all)."""
    try:
        if cell == "-":
            return None
        if cell == "H":
            return CellSpec(visible=False, level=None, beam=False, icon=False)
        match = CELL_PATTERN.match(cell)
        if not match:
            raise ValueError(f"bad cell {cell!r}")
        return CellSpec(visible=True, level=int(match.group(1)), beam=bool(match.group(2)),
                        icon=bool(match.group(3)))
    except Exception:
        LOGGER.exception("parse_cell failed: %r", cell)
        raise
