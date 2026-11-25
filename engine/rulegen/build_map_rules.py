"""Generate config/band_rules_map_items.csv from the agreed map item rule (user, 2026-11-14).

WHAT: Waystone rows per tier (T1-T16) and one row per other map item class; one column per band.
WHY:  The waystone part is mechanical; generating it avoids transcription errors.
HOW:  Waystones: tier N drops from area level waystone_base + N (T1 @58 per RePoE is the one
      exception, given separately); per band the visible tiers relative to the band's top tier
      follow the windows below. Other classes: one fixed cell from their RePoE drop level on.
      Icons: level-3 waystones and every other map item ("i"). --dry-run prints only.
"""
import argparse
import csv
import io
import sys
import tomllib

# band min -> list of (lowest tier, highest tier, cell); tiers not listed but droppable are hidden
WAYSTONE_WINDOWS = {
    46: [(1, 1, "3i")],
    61: [(6, 6, "3i"), (4, 5, "2"), (1, 3, "1")],
    71: [(10, 11, "3i"), (7, 9, "2"), (4, 6, "1"), (1, 3, "0")],
    76: [(15, 16, "3i"), (12, 14, "2"), (9, 11, "1"), (6, 8, "0")],
    81: [(16, 16, "3i"), (14, 15, "2"), (11, 13, "1"), (8, 10, "0")],
    86: [(16, 16, "3i"), (14, 15, "2"), (11, 13, "1"), (8, 10, "0")],
}
# filter class, rarity, drop level (RePoE minimum), cell, note
OTHER_ITEMS = [
    ("Tablet", "normal_magic", 65, "2i", ""),
    ("Tablet", "rare", 65, "3i", "may be moved to family 1 per band"),
    ("Pinnacle Keys", "any", 1, "4i", "drop_level 1 from RePoE is not a real limit"),
    ("Vault Keys", "any", 35, "3i", "drop_level varies per key (35-68)"),
    ("Relics", "any", 1, "2i", "drop_level varies per relic (1-78)"),
    ("Trial Coins", "any", 24, "2i", "drop_level varies per coin (24-65)"),
]


def waystone_drop_level(tier):
    """RePoE 0.5.5.9: T1 @58, T2 @66 ... T16 @80."""
    try:
        return 58 if tier == 1 else 64 + tier
    except Exception as error:
        print(f"\033[91mWaystone drop level failed (T{tier}): {error}\033[0m")
        raise


def waystone_cell(tier, band):
    try:
        if waystone_drop_level(tier) > band["max"]:
            return "-"
        for low, high, cell in WAYSTONE_WINDOWS.get(band["min"], []):
            if low <= tier <= high:
                return cell
        return "H"
    except Exception as error:
        print(f"\033[91mWaystone cell failed (T{tier}, {band}): {error}\033[0m")
        raise


def build_rows(bands):
    try:
        rows = []
        for tier in range(1, 17):
            cells = [waystone_cell(tier, band) for band in bands]
            rows.append(["*", "class", "Waystones", "any", "6", str(waystone_drop_level(tier)), str(tier)] + cells + [""])
        for item_class, rarity, drop, cell, note in OTHER_ITEMS:
            cells = ["-" if drop > band["max"] else cell for band in bands]
            rows.append(["*", "class", item_class, rarity, "6", str(drop), ""] + cells + [note])
        return rows
    except Exception as error:
        print(f"\033[91mRow build failed: {error}\033[0m")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("structure")
    parser.add_argument("output_csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        with open(args.structure, "rb") as handle:
            bands = tomllib.load(handle)["output"]["bands"]
        missing = [b["min"] for b in bands if b["min"] >= 46 and b["min"] not in WAYSTONE_WINDOWS]
        if missing:
            print(f"\033[91mNo waystone window for bands starting at {missing}\033[0m")
            sys.exit(1)
        header = ["name", "match", "item_class", "rarity", "family", "drop_level", "waystone_tier"] \
            + [f"{b['min']}-{b['max']}" for b in bands] + ["note"]
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(build_rows(bands))
        text = buffer.getvalue()
        if any(ord(ch) > 127 for ch in text):
            print("\033[91mNon-ASCII character in output.\033[0m")
            sys.exit(1)
        if args.dry_run:
            print(text)
            print("\033[92mDry run OK, nothing written.\033[0m")
            return
        with open(args.output_csv, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        print(f"\033[92mWritten: {args.output_csv}\033[0m")
    except SystemExit:
        raise
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
