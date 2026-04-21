"""utils/logger.py — Shared logger."""
import logging
import os
from pathlib import Path

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        ))
        logger.addHandler(handler)
        # Optional file logging
        log_file = os.getenv("LOG_FILE", "")
        if log_file:
            try:
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                fh = logging.FileHandler(log_file, encoding="utf-8")
                fh.setFormatter(handler.formatter)
                logger.addHandler(fh)
            except Exception:
                pass
    return logger
