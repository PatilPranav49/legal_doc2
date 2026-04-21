"""
utils/key_rotation.py — Automatic API key rotation across 3 Sarvam accounts
"""

import threading
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class SarvamKeyRotator:
    """
    Manages rotation across up to 3 Sarvam API keys.
    Automatically switches to next key on exhaustion or error.
    Thread-safe for concurrent use.
    """

    def __init__(self):
        self._keys = Config.SARVAM_API_KEYS.copy()
        self._index = 0
        self._lock = threading.Lock()
        self._failed_keys = set()

        if not self._keys:
            logger.warning(
                "No Sarvam API keys found. Add keys to .env file. "
                "Running in DEMO MODE — API calls will be simulated."
            )
        else:
            logger.info(f"KeyRotator initialized with {len(self._keys)} API key(s).")

    @property
    def current_key(self) -> str | None:
        with self._lock:
            available = [k for k in self._keys if k not in self._failed_keys]
            if not available:
                return None
            return available[self._index % len(available)]

    def rotate(self) -> str | None:
        """Move to next available key."""
        with self._lock:
            available = [k for k in self._keys if k not in self._failed_keys]
            if not available:
                logger.error("All API keys exhausted or failed!")
                return None
            self._index = (self._index + 1) % len(available)
            logger.info(f"Rotated to key index {self._index + 1}")
            return available[self._index]

    def mark_failed(self, key: str):
        """Mark a key as failed (e.g. credits exhausted)."""
        with self._lock:
            self._failed_keys.add(key)
            logger.warning(f"Key ending in ...{key[-6:]} marked as failed/exhausted.")

    def get_headers(self) -> dict:
        """Return auth headers for current key."""
        key = self.current_key
        if not key:
            return {}
        return {
            "api-subscription-key": key,
            "Content-Type": "application/json",
        }

    def available_count(self) -> int:
        return len([k for k in self._keys if k not in self._failed_keys])

    def is_demo_mode(self) -> bool:
        return len(self._keys) == 0


# Singleton instance
_rotator = None


def get_key_rotator() -> SarvamKeyRotator:
    global _rotator
    if _rotator is None:
        _rotator = SarvamKeyRotator()
    return _rotator
