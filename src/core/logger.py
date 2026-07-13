"""Logging system with rotation support."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(workspace_root: Path) -> logging.Logger:
    """Initialize logging with rotation.

    Creates .ManualAid/Logs/log.log with 1 MB per file, 10 backups.
    Returns the root logger named 'manualaid'.
    """
    if not isinstance(workspace_root, Path):
        workspace_root = Path(workspace_root)
    log_dir = workspace_root / ".ManualAid" / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "log.log"

    handler = RotatingFileHandler(log_file, maxBytes=1_048_576, backupCount=10, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    logger = logging.getLogger("manualaid")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger
