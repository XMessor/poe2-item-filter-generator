"""Layered config: a player profile on top of the default config/.

WHAT: Resolves every config file profile-first, then config/, and deep-merges the profile's
      structure.toml over the default one.
WHY:  A player keeps only the files and keys they changed (profiles/<name>/), so a maintainer
      update of config/ still reaches everything the player did not touch (user, 2026-11-25).
HOW:  ConfigLayers answers `layers / "file.csv"` with a Path, like a folder does, so every
      consumer that joins the config folder with a file name works unchanged. Merge rule of
      structure.toml: tables merge key by key; any other value in the profile (a list, a string,
      a number) replaces the default value whole - e.g. a profile `bands` list replaces all bands.
"""
import tomllib
from dataclasses import dataclass
from pathlib import Path

from engine.logsetup import get_logger

LOGGER = get_logger("profile")
STRUCTURE_FILE = "structure.toml"


# ----------------------------------------------------------------------------------------------
# Layers
# WHAT: the two folders and the file lookup across them.
# WHY:  a profile file replaces the default file of the same name; a file the profile does not
#       have comes from config/.
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ConfigLayers:
    base: Path
    profile: Path | None = None

    def __truediv__(self, name):
        """Path of one config file: the profile's copy if it has one, else the default."""
        try:
            if self.profile is not None and (self.profile / name).exists():
                return self.profile / name
            return self.base / name
        except Exception:
            LOGGER.exception("file lookup failed: %r in %s", name, self)
            raise

    def __str__(self):
        try:
            return f"{self.base} + profile {self.profile}" if self.profile else str(self.base)
        except Exception:
            LOGGER.exception("ConfigLayers str failed")
            raise

    def profile_files(self):
        """Names of the files in the profile folder (empty without a profile)."""
        try:
            if self.profile is None:
                return []
            return sorted(path.name for path in self.profile.iterdir() if path.is_file())
        except Exception:
            LOGGER.exception("profile_files failed: %s", self)
            raise


# ----------------------------------------------------------------------------------------------
# structure.toml
# WHAT: reading and the deep merge.
# ----------------------------------------------------------------------------------------------
def read_toml(path):
    """Parsed TOML file."""
    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except Exception:
        LOGGER.exception("read_toml failed: %s", path)
        raise


def merge_tables(default, override):
    """Deep merge: tables key by key, every other value replaced by the override."""
    try:
        merged = dict(default)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = merge_tables(merged[key], value)
            else:
                merged[key] = value
        return merged
    except Exception:
        LOGGER.exception("merge_tables failed: keys %r", list(override))
        raise


def load_config(config_dir, profile_dir=None):
    """(ConfigLayers, structure) of the default config with an optional profile on top."""
    try:
        layers = ConfigLayers(Path(config_dir), Path(profile_dir) if profile_dir else None)
        if layers.profile is not None and not layers.profile.is_dir():
            raise FileNotFoundError(f"profile folder not found: {layers.profile}")
        structure = read_toml(layers.base / STRUCTURE_FILE)
        if layers.profile is not None and (layers.profile / STRUCTURE_FILE).exists():
            structure = merge_tables(structure, read_toml(layers.profile / STRUCTURE_FILE))
        return layers, structure
    except Exception:
        LOGGER.exception("load_config failed: config=%r profile=%r", config_dir, profile_dir)
        raise
