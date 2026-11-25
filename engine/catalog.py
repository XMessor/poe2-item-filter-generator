"""RePoE catalog: the base items the engine works with.

WHAT: Loads a RePoE PoE2 snapshot (base_items + item_classes) into BaseItem records with the
      fields the engine needs: name, RePoE class id, filter class name, drop level, level
      requirement, attribute group, implicits, defence group. --export writes these records to
      the reduced catalog (structure.toml [repoe] catalog_*), which is read when no RePoE
      snapshot is present.
WHY:  Every later step (config validation, sections, equipment tiering, simulation, diff) reads
      the same normalised view, so the RePoE field semantics live in one place. The reduced
      catalog lets a player build without RePoE's own files, which may not be redistributed
      (NOTICE.md; user 2026-11-25).
HOW:  Only `released` items with a real name are kept ([DNT placeholders dropped). A name that
      occurs several times in one class collapses to its lowest drop level. The attribute group
      comes from the `<attr>_armour` tag (armour) or the attribute requirements (weapons).
      Source order: RePoE snapshot (the maintainer's source of truth), else the reduced catalog.
      Without --repoe-version every CLI of the engine uses structure.toml [repoe] version.
      Usage: python -E -s -m engine.catalog [--repoe-version 0.5.5.9] [--structure ...] [--export] [--dry-run]
"""
import argparse
import json
import sys
import tomllib
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from engine.logsetup import get_logger

LOGGER = get_logger("catalog")
# RePoE requirement keys in the order of the attribute group names (str_dex_int); format field.
ATTRIBUTE_KEYS = (("str", "strength"), ("dex", "dexterity"), ("int", "intelligence"))
# RePoE defence properties in the same order (str = armour, dex = evasion, int = energy shield).
DEFENCE_KEYS = (("str", "armour"), ("dex", "evasion"), ("int", "energy_shield"))


# ----------------------------------------------------------------------------------------------
# Records
# WHAT: the immutable base item record and the catalog container with its lookups.
# WHY:  frozen dataclasses keep the catalog read-only for every consumer.
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class BaseItem:
    name: str
    repoe_class: str
    filter_class: str
    drop_level: int
    level_requirement: int | None
    attribute_group: str | None
    implicits: tuple
    defence_group: str | None   # from the base defence values: "str_dex" = armour + evasion


@dataclass
class Catalog:
    version: str
    bases: list
    repoe_to_filter: dict

    def names(self, filter_class=None, repoe_class=None):
        """Names of the bases, optionally restricted to one class (either namespace)."""
        try:
            return {base.name for base in self.bases
                    if (filter_class is None or base.filter_class == filter_class)
                    and (repoe_class is None or base.repoe_class == repoe_class)}
        except Exception:
            LOGGER.exception("names failed: filter_class=%r repoe_class=%r", filter_class, repoe_class)
            raise

    def find(self, name):
        """All bases with exactly this name (a name may exist in several classes)."""
        try:
            return [base for base in self.bases if base.name == name]
        except Exception:
            LOGGER.exception("find failed: name=%r", name)
            raise


# ----------------------------------------------------------------------------------------------
# Loading
# WHAT: snapshot path resolution, JSON reading, filtering and normalisation.
# HOW:  file names come from structure.toml [repoe] + the version switch.
# ----------------------------------------------------------------------------------------------
def snapshot_path(project_root, repoe_config, version, file):
    """Path of one RePoE snapshot file, e.g. .infodump/repoe_poe2_0.5.5.9_base_items.json."""
    try:
        name = repoe_config["file_pattern"].format(version=version, file=file)
        return Path(project_root) / repoe_config["folder"] / name
    except Exception:
        LOGGER.exception("snapshot_path failed: version=%r file=%r", version, file)
        raise


def attribute_group(entry):
    """`str`, `dex_int`, ... from the armour tag, else from the requirements; None if neither."""
    try:
        for tag in entry["tags"]:
            if tag.endswith("_armour") and tag != "body_armour":
                return tag[: -len("_armour")]
        requirements = entry.get("requirements") or {}
        parts = [short for short, key in ATTRIBUTE_KEYS if (requirements.get(key) or 0) > 0]
        return "_".join(parts) or None
    except Exception:
        LOGGER.exception("attribute_group failed: name=%r", entry.get("name"))
        raise


def defence_group(entry):
    """`str`, `dex_int`, ... from the base armour / evasion / energy shield values; None if none."""
    try:
        properties = entry.get("properties") or {}
        parts = [short for short, key in DEFENCE_KEYS if (properties.get(key) or {}).get("max", 0) > 0]
        return "_".join(parts) or None
    except Exception:
        LOGGER.exception("defence_group failed: name=%r", entry.get("name"))
        raise


def is_kept(entry):
    """Released items with a real name; [DNT and other bracketed placeholders are dropped."""
    try:
        return entry["release_state"] == "released" and bool(entry["name"]) and not entry["name"].startswith("[")
    except Exception:
        LOGGER.exception("is_kept failed: entry=%r", entry.get("name"))
        raise


def build_bases(raw_items, repoe_to_filter):
    """BaseItem list; duplicate (name, class) pairs collapse to their lowest drop level."""
    try:
        chosen = {}
        for entry in raw_items.values():
            if not is_kept(entry):
                continue
            key = (entry["name"], entry["item_class"])
            if key in chosen and chosen[key]["drop_level"] <= entry["drop_level"]:
                continue
            chosen[key] = entry
        bases = []
        for (name, repoe_class), entry in sorted(chosen.items()):
            requirements = entry.get("requirements") or {}
            bases.append(BaseItem(
                name=name, repoe_class=repoe_class,
                filter_class=repoe_to_filter.get(repoe_class, repoe_class),
                drop_level=entry["drop_level"], level_requirement=requirements.get("level"),
                attribute_group=attribute_group(entry),
                implicits=tuple(entry.get("implicits") or ()),
                defence_group=defence_group(entry)))
        return bases
    except Exception:
        LOGGER.exception("build_bases failed: %d raw entries", len(raw_items))
        raise


def load_repoe(project_root, repoe_config, version):
    """Catalog built from one RePoE snapshot version."""
    try:
        with open(snapshot_path(project_root, repoe_config, version, "base_items"), encoding="utf-8") as handle:
            raw_items = json.load(handle)
        with open(snapshot_path(project_root, repoe_config, version, "item_classes"), encoding="utf-8") as handle:
            raw_classes = json.load(handle)
        repoe_to_filter = {key: value["name"] for key, value in raw_classes.items() if value.get("name")}
        return Catalog(version=version, bases=build_bases(raw_items, repoe_to_filter),
                       repoe_to_filter=repoe_to_filter)
    except Exception:
        LOGGER.exception("load_repoe failed: version=%r root=%r", version, project_root)
        raise


def resolve_version(cli_version, repoe_config):
    """The --repoe-version switch if given, else structure.toml [repoe] version."""
    try:
        return cli_version or repoe_config["version"]
    except Exception:
        LOGGER.exception("resolve_version failed: cli=%r", cli_version)
        raise


def load_catalog(project_root, repoe_config, version):
    """Catalog of one version: from the RePoE snapshot if present, else from the reduced catalog."""
    try:
        if snapshot_path(project_root, repoe_config, version, "base_items").exists():
            LOGGER.info("catalog %s from the RePoE snapshot", version)
            return load_repoe(project_root, repoe_config, version)
        path = catalog_path(project_root, repoe_config, version)
        if not path.exists():
            raise FileNotFoundError(f"no catalog for version {version}: neither "
                                    f"{snapshot_path(project_root, repoe_config, version, 'base_items')} nor {path}")
        LOGGER.info("catalog %s from the reduced catalog %s", version, path)
        return read_reduced(path)
    except Exception:
        LOGGER.exception("load_catalog failed: version=%r root=%r", version, project_root)
        raise


# ----------------------------------------------------------------------------------------------
# Reduced catalog
# WHAT: writing and reading data/catalog_<version>.json.
# WHY:  the public repo ships this file instead of RePoE's own files (NOTICE.md).
# HOW:  one base per line, so a version update shows up as a readable line diff. The records are
#       stored in catalog order and read back unchanged, so a build from either source is identical.
# ----------------------------------------------------------------------------------------------
def catalog_path(project_root, repoe_config, version):
    """Path of the reduced catalog of one version, e.g. data/catalog_0.5.5.9.json."""
    try:
        return Path(project_root) / repoe_config["catalog_folder"] / repoe_config["catalog_pattern"].format(version=version)
    except Exception:
        LOGGER.exception("catalog_path failed: version=%r", version)
        raise


def reduced_text(catalog, source_url):
    """JSON text of the reduced catalog: header fields, then one base per line."""
    try:
        header = {"version": catalog.version,
                  "source": f"Derived from the RePoE PoE2 export ({source_url}). "
                            "Game data (c) Grinding Gear Games; see NOTICE.md.",
                  "item_classes": catalog.repoe_to_filter}
        lines = [json.dumps(asdict(base), ensure_ascii=False) for base in catalog.bases]
        head = json.dumps(header, ensure_ascii=False, indent=1)[:-2]
        return head + ',\n "bases": [\n' + ",\n".join(lines) + "\n ]\n}\n"
    except Exception:
        LOGGER.exception("reduced_text failed: version=%r", catalog.version)
        raise


def read_reduced(path):
    """Catalog read from a reduced catalog file."""
    try:
        with open(path, encoding="utf-8") as handle:
            stored = json.load(handle)
        bases = [BaseItem(**dict(record, implicits=tuple(record["implicits"]))) for record in stored["bases"]]
        return Catalog(version=stored["version"], bases=bases, repoe_to_filter=stored["item_classes"])
    except Exception:
        LOGGER.exception("read_reduced failed: %s", path)
        raise


# ----------------------------------------------------------------------------------------------
# CLI
# WHAT: loads a catalog and prints a per-class summary; --export writes the reduced catalog
#       from the RePoE snapshot (--dry-run: report the target, write nothing).
# ----------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repoe-version", default=None, help="default: structure.toml [repoe] version")
    parser.add_argument("--structure", default="config/structure.toml")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--export", action="store_true", help="write the reduced catalog from the RePoE snapshot")
    parser.add_argument("--dry-run", action="store_true", help="with --export: write nothing")
    args = parser.parse_args()
    try:
        with open(args.structure, "rb") as handle:
            repoe = tomllib.load(handle)["repoe"]
        version = resolve_version(args.repoe_version, repoe)
        catalog = load_repoe(args.project_root, repoe, version) if args.export \
            else load_catalog(args.project_root, repoe, version)
        counts = Counter(base.filter_class for base in catalog.bases)
        for filter_class, count in sorted(counts.items()):
            print(f"{count:5}  {filter_class}")
        print(f"\033[92mCatalog {catalog.version}: {len(catalog.bases)} bases in {len(counts)} classes.\033[0m")
        if args.export:
            target = catalog_path(args.project_root, repoe, version)
            text = reduced_text(catalog, repoe["base_url"])
            if args.dry_run:
                print(f"\033[93mDry run: {len(text.encode('utf-8'))} bytes would be written to {target}.\033[0m")
                return
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
            print(f"\033[92mReduced catalog written: {target} ({len(text.encode('utf-8'))} bytes).\033[0m")
    except Exception as error:
        LOGGER.exception("catalog CLI failed: %r", vars(args))
        print(f"\033[91mCatalog failed: {error} (details: .log/engine.log)\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
