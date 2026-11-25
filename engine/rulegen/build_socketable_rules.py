"""Generate config/band_rules_socketables.csv: socketables (family 13) per band.

WHAT: One row per item of the RePoE "SoulCore" class (runes, soul cores, idols, named runes),
      grouped by the agreed rules (user, 2026-11-14).
WHY:  Same mechanism as the league items - shared code in build_league_rules.py.
HOW:  First matching group wins; the catch-all last group takes every remaining @65 named item.
      Usage: same arguments as build_league_rules.py (repoe, structure, output, --dry-run).
"""
from build_league_rules import run

CLASS = "SoulCore"
# (label, family, regex, item class, fixed cells or None, cell from drop level)
GROUPS = [
    ("greater rune of", 13, r"^Greater Rune of ", CLASS, None, "4i"),
    ("ancient rune of", 13, r"^Ancient Rune of ", CLASS, None, "3"),
    ("warding rune of", 13, r"^Warding Rune of ", CLASS, None, "2"),
    ("rune of", 13, r"^Rune of ", CLASS, None, "2"),
    ("perfect rune", 13, r"^Perfect .+ Rune$", CLASS, ["-", "-", "-", "-", "3", "3", "3", "3", "3"], None),
    ("greater rune", 13, r"^Greater .+ Rune$", CLASS, ["-", "-", "-", "3", "2", "2", "2", "2", "2"], None),
    ("lesser rune", 13, r"^Lesser .+ Rune$", CLASS, ["3", "3", "2", "1", "0", "0", "0", "0", "0"], None),
    ("rune", 13, r"^\S+ Rune$", CLASS, ["-", "-", "3", "2", "1", "1", "1", "1", "1"], None),
    ("soul core", 13, r"Soul Core", CLASS, None, "3"),
    ("idol", 13, r"\bIdol\b", CLASS, None, "3"),    # "Bear Idol" and "Idol of Alira" alike
    ("named 65", 13, r".", CLASS, None, "4bi"),
]
MIN_DROP = {"named 65": 65}

if __name__ == "__main__":
    run(GROUPS, MIN_DROP)
