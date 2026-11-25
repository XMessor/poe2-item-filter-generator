"""Shared logger of the engine.

WHAT: One logger per module, writing to <project>/.log/engine.log and to the console.
WHY:  The clean-code rule requires every caught exception to be logged to the .log folder with
      its inputs before it is re-raised; one shared setup avoids repeating the handler code.
HOW:  The project root is the parent of the engine package; the handler is added once.
"""
import logging
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / ".log" / "engine.log"


def get_logger(name):
    """Return the engine logger for a module (file handler added on first use)."""
    try:
        logger = logging.getLogger("engine")
        if not logger.handlers:
            LOG_FILE.parent.mkdir(exist_ok=True)
            handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger.getChild(name)
    except Exception as error:
        print(f"\033[91mLogger setup failed ({LOG_FILE}): {error}\033[0m")
        raise
