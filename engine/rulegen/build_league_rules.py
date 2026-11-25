"""Generate config/band_rules_league.csv: league items (families 5, 8, 9) per band.

WHAT: One row per exact item name, taken from the RePoE export, grouped by the agreed rules
      (user, 2026-11-14); one column per band.
WHY:  Exact names avoid ambiguous substring matches (e.g. "Refined" also matches a ring), and
      taking names from RePoE avoids typing them.
HOW:  Each item is assigned to the FIRST group whose regex matches (order = priority). A group
      has either fixed per-band cells (tiered essences) or one cell applied from the item's
      RePoE drop level on ("-" before). Prints group counts; --dry-run writes nothing.
"""
import argparse
import csv
import io
import json
import re
import sys
import tomllib

ESSENCE_SPECIAL = r"^Essence of (Delirium|Horror|Hysteria|Insanity|the Abyss|the Breach)$"
# (label, family, regex, item class, fixed cells or None, cell from drop level)
GROUPS = [
    ("special essence", 8, ESSENCE_SPECIAL, "StackableCurrency", None, "4i"),
    ("perfect essence", 8, r"^Perfect Essence of ", "StackableCurrency", ["-", "-", "-", "-", "-", "3", "3", "3", "3"], None),
    ("greater essence", 8, r"^Greater Essence of ", "StackableCurrency", ["-", "-", "-", "3", "3", "2", "2", "2", "2"], None),
    ("lesser essence", 8, r"^Lesser Essence of ", "StackableCurrency", ["3", "3", "2", "2", "1", "0", "0", "0", "0"], None),
    ("essence", 8, r"^Essence of ", "StackableCurrency", ["-", "-", "3", "3", "2", "1", "1", "1", "1"], None),
    ("refined catalyst", 8, r"^Refined .+ Catalyst$", "StackableCurrency", None, "3"),
    ("catalyst", 8, r"Catalyst$", "StackableCurrency", None, "2"),
    ("concentrated liquid", 8, r"^(Ancient )?Concentrated Liquid ", "StackableCurrency", None, "4i"),
    ("potent liquid", 8, r"^(Ancient )?Potent Liquid ", "StackableCurrency", None, "3"),
    ("diluted liquid", 8, r"^(Ancient )?Diluted Liquid ", "StackableCurrency", None, "1"),
    ("liquid", 8, r"^(Ancient )?Liquid (Despair|Disgust|Envy|Paranoia)$", "StackableCurrency", None, "2"),
    ("expedition artifact", 8, r"^(Black Scythe|Broken Circle|Order|Sun) Artifact$", "StackableCurrency", None, "2"),
    ("exotic coinage", 8, r"^Exotic Coinage$", "StackableCurrency", None, "3"),
    ("splinter", 8, r"^(Breach|Petition|Ritual|Runic|Simulacrum) Splinter$", "StackableCurrency", None, "2"),
    ("revelatory wombgift", 8, r"^Revelatory Wombgift$", "BrequelFruit", None, "2b"),  # one level up, sound + beam
    ("wombgift", 8, r"Wombgift$", "BrequelFruit", None, "1"),   # Breach endgame currency (user 2026-11-14)
    ("bronze key", 8, r"^Bronze Key$", "StackableCurrency", None, "1"),
    ("silver key", 8, r"^Silver Key$", "StackableCurrency", None, "2"),
    ("gold key", 8, r"^Gold Key$", "StackableCurrency", None, "3"),
    ("gnawed bone", 5, r"^Gnawed (Collarbone|Jawbone|Rib)$", "StackableCurrency", None, "1"),
    ("preserved bone", 5, r"^Preserved (Collarbone|Jawbone|Rib)$", "StackableCurrency", None, "2"),
    ("preserved rare bone", 5, r"^Preserved (Cranium|Vertebrae)$", "StackableCurrency", None, "3"),
    ("ancient bone", 5, r"^Ancient (Collarbone|Jawbone|Rib)$", "StackableCurrency", None, "3"),
    ("altered collarbone", 5, r"^Altered Collarbone$", "StackableCurrency", None, "3"),
    ("omen 80", 9, r".", "Omen", None, "4i"),     # drop level 80; filtered below by min_drop
    ("omen", 9, r".", "Omen", None, "3"),
]
MIN_DROP = {"omen 80": 80}


def load_names(repoe_path):
    """Return {name: drop_level} for released items per item class (duplicates collapsed)."""
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


def ascii_match(name, class_names):
    """Exact name if ASCII; otherwise the longest ASCII run of the name as a substring match,
    because the rule CSVs must stay ASCII (Excel/Windows encoding). The run must match only this
    name in the whole catalog ("Morrigan" -> "rrigan's Insight", not "M"), else it is an error."""
    try:
        if name.isascii():
            return name, "exact"
        run = max(re.split(r"[^\x00-\x7f]+", name), key=len).strip()
        hits = [other for other in class_names if run in other]
        if hits != [name]:
            raise ValueError(f"ASCII run {run!r} of {name!r} matches {hits}")
        return run, "contains"
    except Exception as error:
        print(f"\033[91mascii_match failed: {error}\033[0m")
        raise


def assign_rows(by_class, bands, groups=GROUPS, min_drop=MIN_DROP):
    try:
        rows, counts, taken = [], {}, set()
        all_names = set().union(*by_class.values())   # BaseType match spans every class
        for label, family, pattern, item_class, fixed, cell in groups:
            counts[label] = 0
            for name, drop in sorted(by_class.get(item_class, {}).items()):
                if name in taken or not re.search(pattern, name) or drop < min_drop.get(label, 0):
                    continue
                cells = fixed if fixed else ["-" if drop > band["max"] else cell for band in bands]
                match_name, match = ascii_match(name, all_names)
                rows.append([match_name, match, str(family), str(drop)] + list(cells) + [label])
                taken.add(name)
                counts[label] += 1
        return rows, counts
    except Exception as error:
        print(f"\033[91mRow assignment failed: {error}\033[0m")
        raise


def run(groups, min_drop):
    """Shared entry point: parse arguments, build rows from the given groups, write the CSV."""
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("repoe_base_items")
        parser.add_argument("structure")
        parser.add_argument("output_csv")
        parser.add_argument("--dry-run", action="store_true")
        args = parser.parse_args()
        with open(args.structure, "rb") as handle:
            bands = tomllib.load(handle)["output"]["bands"]
        if any(fixed and len(fixed) != len(bands) for *_rest, fixed, _cell in groups):
            print("\033[91mFixed cell count does not match band count.\033[0m")
            sys.exit(1)
        rows, counts = assign_rows(load_names(args.repoe_base_items), bands, groups, min_drop)
        print("\033[93mgroup counts:\033[0m", counts)
        header = ["name", "match", "family", "drop_level"] + [f"{b['min']}-{b['max']}" for b in bands] + ["note"]
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
        text = buffer.getvalue()
        if any(ord(ch) > 127 for ch in text):
            print("\033[91mNon-ASCII character in output.\033[0m")
            sys.exit(1)
        if args.dry_run:
            print(f"\033[92mDry run OK ({len(rows)} rows), nothing written.\033[0m")
            return
        with open(args.output_csv, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        print(f"\033[92mWritten: {args.output_csv} ({len(rows)} rows)\033[0m")
    except SystemExit:
        raise
    except Exception as error:
        print(f"\033[91mLeague rule generation failed: {error}\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    run(GROUPS, MIN_DROP)
