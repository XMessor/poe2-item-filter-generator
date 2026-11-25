"""Entry point of the v1.0 engine: config + RePoE -> filter files.

WHAT: Validates the config against the RePoE catalog, builds every supported section in the
      order of structure.toml [output] sections, and writes the per-band files and the AreaLevel
      file into the output folder.
WHY:  One command for the whole pipeline; the `update poe2` skill will call this.
HOW:  A config error stops the build before anything is written. Sections this build step
      cannot produce yet are listed and skipped. --dry-run builds everything in memory and
      prints the block counts, writing nothing.
      --profile DIR layers a player profile over config/ (engine/profile.py).
      Usage: python -E -s -m engine.build [--repoe-version 0.5.5.9] [--profile DIR] [--out DIR] [--only a,b] [--dry-run]
"""
import argparse
import sys
from pathlib import Path

from engine.catalog import load_catalog, resolve_version
from engine.config import print_report, read_csv, validate
from engine.logsetup import get_logger
from engine.profile import load_config
from engine.render import render_file
from engine.equipment import build_equipment, build_jewellery, with_salvage
from engine.sections import build_band_table

LOGGER = get_logger("build")


def section_rules(section, config_dir, structure, catalog, overrides, mode):
    """Rules of one section: the equipment algorithm, the jewellery table or a band rule CSV
    (with salvage inserted before its Hide rules when the section asks for it)."""
    try:
        name, source = section["name"], section["source"]
        if source == "algorithm":
            return build_equipment(name, config_dir / section["extra"][0], catalog, structure, mode)
        if source == "jewellery.csv":
            return build_jewellery(name, config_dir / source, catalog, structure)
        rules = build_band_table(name, config_dir / source, structure["output"]["bands"], structure, overrides)
        return with_salvage(rules, structure, sockets=False) if section.get("salvage") else rules
    except Exception:
        LOGGER.exception("section_rules failed: %r", section)
        raise


def build_sections(structure, config_dir, catalog, only, mode):
    """[(name, rules)] of the sections in filter order, and the names left out by --only."""
    try:
        built, skipped = [], []
        overrides_path = config_dir / structure["overrides"]["file"]
        overrides = read_csv(overrides_path)[1] if overrides_path.exists() else []
        for section in structure["output"]["sections"]:
            if only and section["name"] not in only:
                skipped.append(section["name"])
                continue
            built.append((section["name"], section_rules(section, config_dir, structure, catalog, overrides, mode)))
        return built, skipped
    except Exception:
        LOGGER.exception("build_sections failed: only=%r", only)
        raise


def output_files(structure, built, meta, suffix=""):
    """{file name: text} of every output file; suffix goes before .filter (droplevel variant)."""
    try:
        output = structure["output"]

        def named(file_name):
            try:
                return file_name.replace(".filter", f"{suffix}.filter")
            except Exception:
                LOGGER.exception("named failed: %r suffix=%r", file_name, suffix)
                raise

        files = {named(output["area_level_file"]): render_file(built, structure, meta)}
        for band in output["bands"]:
            files[named(output["band_file_pattern"].format(**band))] = render_file(built, structure, meta, band)
        return files
    except Exception:
        LOGGER.exception("output_files failed")
        raise


def output_folder(out, config_dir, structure):
    """--out if given; else <profile>/filters for a profile build (a player must never overwrite
    the ready-made samples of the repo); else structure.toml [output] folder."""
    try:
        if out:
            return Path(out)
        if config_dir.profile is not None:
            return config_dir.profile / structure["output"]["profile_folder"]
        return Path(structure["output"]["folder"])
    except Exception:
        LOGGER.exception("output_folder failed: out=%r config=%s", out, config_dir)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repoe-version", default=None, help="default: structure.toml [repoe] version")
    parser.add_argument("--config", default="config")
    parser.add_argument("--profile", default=None, help="player profile folder layered over --config")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--out", default=None,
                        help="default: <profile>/filters with --profile, else structure.toml [output] folder")
    parser.add_argument("--only", default="", help="comma-separated section names (default: all)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        config_dir, structure = load_config(args.config, args.profile)
        version = resolve_version(args.repoe_version, structure["repoe"])
        catalog = load_catalog(args.project_root, structure["repoe"], version)
        if print_report(validate(config_dir, structure, catalog)):
            print("\033[91mConfig has errors - nothing built.\033[0m")
            sys.exit(1)
        only = {name.strip() for name in args.only.split(",") if name.strip()}
        built, skipped = build_sections(structure, config_dir, catalog, only, "names")
        built_drop, _skipped = build_sections(structure, config_dir, catalog, only, "droplevel")
        meta = {"filter_version": structure["output"]["version"], "repoe_version": version,
                "sections": [name for name, _rules in built]}
        files = output_files(structure, built, meta)
        files.update(output_files(structure, built_drop, dict(meta, filter_version=meta["filter_version"] + " droplevel"),
                                  structure["output"]["droplevel_suffix"]))
        for name, rules in built:
            print(f"{len(rules):5} blocks  {name}")
        if skipped:
            print(f"\033[93mLeft out (--only):{', '.join(skipped)}\033[0m")
        out_dir = output_folder(args.out, config_dir, structure)
        if args.dry_run:
            print(f"\033[92mDry run OK: {len(files)} files would be written to {out_dir}.\033[0m")
            return
        out_dir.mkdir(parents=True, exist_ok=True)
        for file_name, text in files.items():
            (out_dir / file_name).write_text(text, encoding="utf-8", newline="\n")
        print(f"\033[92mWritten {len(files)} files to {out_dir}.\033[0m")
    except SystemExit:
        raise
    except Exception as error:
        LOGGER.exception("build failed: %r", vars(args))
        print(f"\033[91mBuild failed: {error} (details: .log/engine.log)\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
