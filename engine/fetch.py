"""Fetch the current RePoE PoE2 snapshot into .infodump/.

WHAT: Reads the version from the RePoE index page, and - if that version is not stored yet -
      downloads the configured files (base_items, item_classes) as
      .infodump/repoe_poe2_<version>_<file>.json.
WHY:  The first step of the `update poe2` skill; the version in the file name lets the diff
      compare two snapshots side by side.
HOW:  Downloads go into a fresh, empty staging folder first (downloaded data is untrusted), are
      checked to be non-empty JSON objects, and only then moved into place. Existing snapshots
      are never overwritten unless --force. Only public files are requested, with a generic
      client name (structure.toml [repoe]). --dry-run prints the version and the plan only.
      Usage: python -E -s -m engine.fetch [--structure config/structure.toml] [--force] [--dry-run]
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
import tomllib
import urllib.request
from pathlib import Path

from engine.catalog import snapshot_path
from engine.logsetup import get_logger

LOGGER = get_logger("fetch")
TIMEOUT_SECONDS = 60


def http_get(url, user_agent):
    """Response body of one GET request (bytes)."""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except Exception:
        LOGGER.exception("http_get failed: %s", url)
        raise


def current_version(repoe):
    """Version string from the index page title, e.g. '0.5.5.9'."""
    try:
        page = http_get(repoe["base_url"], repoe["user_agent"]).decode("utf-8", errors="replace")
        match = re.search(repoe["version_pattern"], page)
        if not match:
            raise ValueError(f"no version matching {repoe['version_pattern']!r} on {repoe['base_url']}")
        return match.group(1)
    except Exception:
        LOGGER.exception("current_version failed: %s", repoe.get("base_url"))
        raise


def download_checked(repoe, file, staging):
    """Download one file into the staging folder and check it is a non-empty JSON object."""
    try:
        body = http_get(f"{repoe['base_url']}{file}.json", repoe["user_agent"])
        parsed = json.loads(body)
        if not isinstance(parsed, dict) or not parsed:
            raise ValueError(f"{file}.json is not a non-empty JSON object")
        target = staging / f"{file}.json"
        target.write_bytes(body)
        return target, len(parsed)
    except Exception:
        LOGGER.exception("download_checked failed: %s", file)
        raise


def stored_versions(project_root, repoe):
    """Versions with a stored base_items snapshot, oldest first (numeric order)."""
    try:
        prefix, suffix = repoe["file_pattern"].split("{version}")
        suffix = suffix.format(file="base_items")
        names = [p.name for p in (Path(project_root) / repoe["folder"]).glob(prefix + "*" + suffix)]
        versions = [name[len(prefix):-len(suffix)] for name in names]
        return sorted(versions, key=lambda v: [int(part) if part.isdigit() else -1 for part in v.split(".")])
    except Exception:
        LOGGER.exception("stored_versions failed: %s", project_root)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--structure", default="config/structure.toml")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--force", action="store_true", help="re-download a version already stored")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        with open(args.structure, "rb") as handle:
            repoe = tomllib.load(handle)["repoe"]
        version = current_version(repoe)
        targets = {file: snapshot_path(args.project_root, repoe, version, file) for file in repoe["files"]}
        missing = [file for file, path in targets.items() if args.force or not path.exists()]
        print(f"RePoE version online: \033[93m{version}\033[0m")
        print(f"Stored versions: {', '.join(stored_versions(args.project_root, repoe)) or '-'}")
        if not missing:
            print(f"\033[92mAlready stored: {', '.join(str(p) for p in targets.values())}\033[0m")
            return
        if args.dry_run:
            print(f"\033[92mDry run: would download {', '.join(missing)} for {version}.\033[0m")
            return
        staging = Path(tempfile.mkdtemp(prefix="repoe_staging_", dir=Path(args.project_root) / "tmp"))
        try:
            staged = {file: download_checked(repoe, file, staging) for file in missing}
            for file, (path, entries) in staged.items():
                shutil.move(str(path), targets[file])
                print(f"\033[92mStored {targets[file]} ({entries} entries)\033[0m")
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    except Exception as error:
        LOGGER.exception("fetch CLI failed: %r", vars(args))
        print(f"\033[91mFetch failed: {error} (details: .log/engine.log)\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
