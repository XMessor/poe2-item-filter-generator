"""Generate config/band_rules_gems.csv from the agreed gem rule (user, 2026-11-14).

WHAT: One row per (uncut gem type, gem level) and one row per Lineage support gem; one column
      per band, cells in the agreed ASCII notation (3, 2, 0, 4, H, -).
WHY:  The rule is mechanical; generating the table avoids transcription errors in 43 rows.
HOW:  Skill/Spirit: the three best levels shown (best -> 3, best-1 -> 2, best-2 -> 1, font 21),
      lower hidden; levels above the band maximum count as best (3) (user, 2026-11-15).
      Support: only the best level (3); from band min >= support_low_from it drops to 0 (size 20).
      Lineage supports: level 4 in every band, by exact name from RePoE (possessive-named support
      gems, [DNT] placeholders excluded; non-ASCII names become an ASCII "contains" prefix).
      Skill/Spirit levels above the band maximum count as best (3); support levels above it are "-".
      Band maximums come from --max-* arguments (sources: RePoE drop_level up to level 14 /
      support L5, the user's gem table for skill/spirit L15-20). --dry-run prints only.
"""
import argparse
import csv
import io
import sys
import re
import tomllib

from build_league_rules import ascii_match, load_names

LINEAGE_CLASS = "Support Skill Gem"      # RePoE class id
LINEAGE_PATTERN = r"\w's "               # possessive name, e.g. "Atziri's Allure"


def band_cells(levels, band_max, rule, bands, support_low_from):
    """Return {level: [cell per band]} for one gem type."""
    try:
        table = {}
        for level in levels:
            cells = []
            for band, best in zip(bands, band_max):
                if rule == "top_two":
                    # user 2026-11-15: the three best levels show; above the band counts as best (3)
                    if level >= best:
                        cells.append("3")
                    elif level == best - 1:
                        cells.append("2")
                    elif level == best - 2:
                        cells.append("1")
                    else:
                        cells.append("H")
                elif level > best:
                    cells.append("-")
                else:
                    top = "0" if band["min"] >= support_low_from else "3"
                    cells.append(top if level == best else "H")
            table[level] = cells
        return table
    except Exception as error:
        print(f"\033[91mCell build failed ({rule}): {error}\033[0m")
        raise


def lineage_rows(repoe_path, bands):
    """One level-4 row per Lineage support gem, sorted by name."""
    try:
        by_class = load_names(repoe_path)
        names = by_class.get(LINEAGE_CLASS, {})
        all_names = set().union(*by_class.values())   # BaseType match spans every class
        rows = []
        for name in sorted(n for n in names if re.search(LINEAGE_PATTERN, n)):
            match_name, match = ascii_match(name, all_names)
            rows.append([match_name, match, "16", ""] + ["4"] * len(bands) + ["lineage support"])
        return rows
    except Exception as error:
        print(f"[91mLineage rows failed: {error}[0m")
        raise


def build_rows(bands, args):
    try:
        rows = []
        specs = [
            ("Uncut Skill Gem", 15, range(1, 21), args.max_skill, "top_two"),
            ("Uncut Spirit Gem", 15, range(4, 21), args.max_skill, "top_two"),
            ("Uncut Support Gem", 15, range(1, 6), args.max_support, "best_only"),
        ]
        for name, family, levels, band_max, rule in specs:
            if len(band_max) != len(bands):
                raise ValueError(f"{name}: {len(band_max)} maxima for {len(bands)} bands")
            for level, cells in band_cells(levels, band_max, rule, bands, args.support_low_from).items():
                rows.append([name, "contains", str(family), str(level)] + cells + [""])
        return rows + lineage_rows(args.repoe_base_items, bands)
    except Exception as error:
        print(f"\033[91mRow build failed: {error}\033[0m")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repoe_base_items")
    parser.add_argument("structure")
    parser.add_argument("output_csv")
    parser.add_argument("--max-skill", type=int, nargs="+", required=True)
    parser.add_argument("--max-support", type=int, nargs="+", required=True)
    parser.add_argument("--support-low-from", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        with open(args.structure, "rb") as handle:
            bands = tomllib.load(handle)["output"]["bands"]
        header = ["name", "match", "family", "gem_level"] + [f"{b['min']}-{b['max']}" for b in bands] + ["note"]
        rows = build_rows(bands, args)
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
        text = buffer.getvalue()
        if any(ord(ch) > 127 for ch in text):
            print("\033[91mNon-ASCII character in output.\033[0m")
            sys.exit(1)
        if args.dry_run:
            print(text)
            print(f"\033[92mDry run OK ({len(rows)} rows), nothing written.\033[0m")
            return
        with open(args.output_csv, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        print(f"\033[92mWritten: {args.output_csv} ({len(rows)} rows)\033[0m")
    except SystemExit:
        raise
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
