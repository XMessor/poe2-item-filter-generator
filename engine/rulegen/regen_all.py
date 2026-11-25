"""Regenerate every generated rule CSV in config/ from its rule script.

WHAT: Runs the five rule generators (gems, map items, league, socketables, flasks) with their
      fixed parameters and writes config/band_rules_<name>.csv - or, with --out-dir, into
      another folder (regression check against the current config).
WHY:  The rule is the source of truth (user, 2026-11-14): on a RePoE update the generated CSVs
      are rewritten and the diff shows what changed; manual edits live in config/overrides.csv.
      The hand-written CSVs (currency, jewels_quest, unique, gold, catch_all) are not touched.
HOW:  Each generator runs as a subprocess with the same interpreter, so their own CLI and
      --dry-run stay usable on their own.
      Usage: regen_all.py <repoe base_items> [--config config] [--out-dir DIR] [--dry-run]
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Gem level maxima per band (.docs/filtering_philosophy.md -> 4. Gems), support at level 0 from band 76.
GEM_ARGS = ["--max-skill", "5", "8", "11", "14", "17", "18", "19", "20", "20",
            "--max-support", "1", "2", "4", "5", "5", "5", "5", "5", "5",
            "--support-low-from", "76"]
# output name -> (script, needs the RePoE file, extra arguments)
GENERATORS = {
    "band_rules_gems.csv": ("build_gem_rules.py", True, GEM_ARGS),
    "band_rules_map_items.csv": ("build_map_rules.py", False, []),
    "band_rules_league.csv": ("build_league_rules.py", True, []),
    "band_rules_socketables.csv": ("build_socketable_rules.py", True, []),
    "band_rules_flasks.csv": ("build_flask_rules.py", True, []),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repoe_base_items")
    parser.add_argument("--config", default="config")
    parser.add_argument("--out-dir", default=None, help="default: the config folder")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        # absolute paths: the generators run with cwd = HERE
        config = Path(args.config).resolve()
        out_dir = Path(args.out_dir).resolve() if args.out_dir else config
        repoe = str(Path(args.repoe_base_items).resolve())
        failed = []
        for output, (script, needs_repoe, extra) in GENERATORS.items():
            command = [sys.executable, "-E", "-s", str(HERE / script)]
            command += [repoe] if needs_repoe else []
            command += [str(config / "structure.toml"), str(out_dir / output)] + extra
            command += ["--dry-run"] if args.dry_run else []
            print(f"\033[93m{script}\033[0m")
            # cwd = HERE so that build_socketable_rules can import build_league_rules
            result = subprocess.run(command, cwd=HERE)
            if result.returncode != 0:
                failed.append(script)
        if failed:
            print(f"\033[91mFailed: {', '.join(failed)}\033[0m")
            sys.exit(1)
        print("\033[92mAll generators OK.\033[0m")
    except SystemExit:
        raise
    except Exception as error:
        print(f"\033[91mregen_all failed: {error}\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
