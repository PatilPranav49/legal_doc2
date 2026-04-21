"""
utils/cache.py — Simple JSON-based disk cache (no external dependencies)
Avoids re-processing the same document twice, saving API credits.
"""

import json
import hashlib
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

_cache_instance = None


class DocumentCache:
    """
    File-system cache keyed by content hash + filename + language hint.
    Each cache entry is a JSON file — no external packages required.
    """

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.enabled = True
            logger.info(f"Cache at: {self.cache_dir}")
        except Exception as e:
            logger.warning(f"Cache disabled (could not create dir): {e}")
            self.enabled = False

    def _path(self, key: str) -> Path:
        safe = hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()
        return self.cache_dir / f"{safe}.json"

    def get(self, key: str) -> dict | None:
        if not self.enabled:
            return None
        try:
            p = self._path(key)
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"Cache HIT: {key[:40]}")
                return data
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None

    def set(self, key: str, value: dict):
        if not self.enabled:
            return
        try:
            save = {k: v for k, v in value.items() if k != "cached"}
            with open(self._path(key), "w", encoding="utf-8") as f:
                json.dump(save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def clear(self):
        for p in self.cache_dir.glob("*.json"):
            try:
                p.unlink()
            except Exception:
                pass
        logger.info("Cache cleared.")


def get_cache() -> DocumentCache | None:
    """Return the singleton cache instance (or None if cache disabled via env)."""
    global _cache_instance
    if _cache_instance is None:
        try:
            import os
            if os.getenv("ENABLE_CACHE", "true").lower() == "true":
                _cache_instance = DocumentCache()
        except Exception as e:
            logger.warning(f"Cache init failed: {e}")
    return _cache_instance
