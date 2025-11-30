import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging() -> None:
    """Configure stdout + rotating file logging for the app.

    - Keeps existing stdout logging behavior.
    - Adds a `logs/edumentor.log` RotatingFileHandler in the repository root.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Ensure a StreamHandler -> stdout exists
    stream_exists = any(
        isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout
        for h in logger.handlers
    )
    if not stream_exists:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    # Add rotating file handler at <repo_root>/logs/edumentor.log
    repo_root = Path(__file__).resolve().parents[1]
    logs_dir = repo_root / "logs"
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # If we can't create the directory, keep running with stdout logging only
        logger.warning("Could not create logs directory: %s", logs_dir)
        return

    log_file = str(logs_dir / "edumentor.log")
    file_handler_exists = any(
        isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == log_file
        for h in logger.handlers
    )
    if not file_handler_exists:
        file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
