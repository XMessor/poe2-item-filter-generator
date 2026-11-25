"""Generate config/band_rules_flasks.csv: flasks and charms (family 12) per band.

WHAT: Life/Mana Flask rows per base, plus one class row for Charms; one column per band.
WHY:  Rule (user, 2026-11-14): of flasks only the best available base matters; of charms only
      rare and better, because they add little and the needed ones are found by the end of act 2.
HOW:  A flask base is shown in a band if it is the best base at ANY area level of the band:
      its drop level falls inside the band, or it is the newest base dropping before the band
      starts (when no base starts exactly at the band minimum). Bases below MIN_FLASK_DROP are
      never shown (user: 1-15 only Greater). Shown bases get levels 0, 1, 2 in ascending drop
      level (sizes 20/25/30), the rest hidden; hidden ones still pass the salvage rule (quality).
      Charms: rare class row at a fixed cell from the lowest charm drop level on; uniques fall to
      the Unique+ rule earlier.
      Usage: build_flask_rules.py <repoe base_items> <structure.toml> <output csv> [--dry-run]
"""
import argparse
import csv
import io
import json
import sys
import tomllib

# RePoE class -> (filter class, colour category in structure.toml)
FLASK_CLASSES = {"LifeFlask": ("Life Flasks", "life_flask"), "ManaFlask": ("Mana Flasks", "mana_flask")}
CHARM_CLASS, CHARM_FILTER_CLASS, CHARM_CATEGORY, CHARM_CELL = "UtilityFlask", "Charms", "charm", "1"
MIN_FLASK_DROP = 10     # Lesser (@1) and Medium (@4) never shown (user, 2026-11-14)


def load_bases(repoe_path):
    """Return {repoe item class: {name: drop_level}} for released, named items."""
    try:
        with open(repoe_path, encoding="utf-8") as handle:
            items = json.load(handle)
        by_class = {}
        for entry in items.values():
            if entry["release_state"] != "released" or not entry["name"] or entry["name"].startswith("["):
                continue
            names = by_class.setdefault(entry["item_class"], {})
            names[entry["name"]] = min(entry["drop_level"], names.get(entry["name"], 999))
        return by_class
    except Exception as error:
        print(f"\033[91mRePoE load failed: {error}\033[0m")
        raise


def flask_cell(drop, drops, band):
    """Cell of one flask base in one band (drops = all drop levels of its class)."""
    try:
        eligible = [d for d in drops if d >= MIN_FLASK_DROP]
        at_start = max([d for d in eligible if d <= band["min"]], default=min(eligible))
        shown = sorted(d for d in eligible if at_start <= d <= band["max"])
        if drop > band["max"]:
            # above the band: still drops now and then (play-test) and counts as best in band
            return str(len(shown) - 1)
        return str(shown.index(drop)) if drop in shown else "H"
    except Exception as error:
        print(f"\033[91mFlask cell failed (@{drop}, {band}): {error}\033[0m")
        raise


def build_rows(by_class, bands):
    try:
        rows = []
        for repoe_class, (filter_class, category) in FLASK_CLASSES.items():
            bases = by_class[repoe_class]
            drops = sorted(bases.values())
            for name, drop in sorted(bases.items(), key=lambda pair: pair[1]):
                cells = [flask_cell(drop, drops, band) for band in bands]
                rows.append([name, "exact", filter_class, "any", "12", category, str(drop)] + cells + [""])
        lowest = min(by_class[CHARM_CLASS].values())
        cells = ["-" if lowest > band["max"] else CHARM_CELL for band in bands]
        rows.append(["*", "class", CHARM_FILTER_CLASS, "rare", "12", CHARM_CATEGORY, str(lowest)] + cells
                    + ["rare only; uniques go to the Unique+ rule"])
        # explicit Hide: without it normal/magic charms would reach the catch-all
        hidden = ["-" if lowest > band["max"] else "H" for band in bands]
        rows.append(["*", "class", CHARM_FILTER_CLASS, "normal_magic", "12", CHARM_CATEGORY, str(lowest)]
                    + hidden + ["hidden; still passes the salvage rule (quality)"])
        return rows
    except Exception as error:
        print(f"\033[91mRow build failed: {error}\033[0m")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repoe_base_items")
    parser.add_argument("structure")
    parser.add_argument("output_csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        with open(args.structure, "rb") as handle:
            bands = tomllib.load(handle)["output"]["bands"]
        rows = build_rows(load_bases(args.repoe_base_items), bands)
        header = (["name", "match", "item_class", "rarity", "family", "category", "drop_level"]
                  + [f"{b['min']}-{b['max']}" for b in bands] + ["note"])
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
