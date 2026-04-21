"""
config.py — Central configuration for Legal Document Analyzer
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Sarvam API Keys (supports up to 3 keys for team rotation) ─────────────
    _raw_keys = [
        os.getenv("SARVAM_API_KEY_1", ""),
        os.getenv("SARVAM_API_KEY_2", ""),
        os.getenv("SARVAM_API_KEY_3", ""),
    ]
    # Filter out empty strings and known placeholder values
    SARVAM_API_KEYS = [
        k for k in _raw_keys
        if k and not k.startswith("your_") and k != ""
    ]

    # ── Sarvam API Endpoints ───────────────────────────────────────────────────
    SARVAM_BASE_URL = "https://api.sarvam.ai"
    SARVAM_OCR_URL = f"{SARVAM_BASE_URL}/v1/ocr"
    SARVAM_TRANSLATE_URL = f"{SARVAM_BASE_URL}/translate"
    SARVAM_LANGUAGE_ID_URL = f"{SARVAM_BASE_URL}/text-lid"

    # ── Supported Indian Languages (all 22 official + common others) ───────────
    INDIC_LANGUAGES = {
        "hi": "Hindi",
        "mr": "Marathi",
        "bn": "Bengali",
        "ta": "Tamil",
        "te": "Telugu",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi",
        "or": "Odia",
        "as": "Assamese",
        "ur": "Urdu",
        "sa": "Sanskrit",
        "ne": "Nepali",
        "doi": "Dogri",
        "kok": "Konkani",
        "mai": "Maithili",
        "mni": "Manipuri",
        "sd": "Sindhi",
        "ks": "Kashmiri",
        "brx": "Bodo",
        "sat": "Santali",
    }

    ENGLISH_CODE = "en"

    # ── Cache settings ─────────────────────────────────────────────────────────
    ENABLE_CACHE =  False
    CACHE_DIR = os.getenv("CACHE_DIR", ".cache")

    # ── File limits ────────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    MAX_PAGES = int(os.getenv("MAX_PAGES_PER_DOC", "100"))

    # ── Supported file types ───────────────────────────────────────────────────
    SUPPORTED_TYPES = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".docx", ".txt", ".webp"]

    # ── Logging ────────────────────────────────────────────────────────────────
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/pipeline.log")

    @classmethod
    def has_api_keys(cls) -> bool:
        return len(cls.SARVAM_API_KEYS) > 0

    @classmethod
    def is_indic_language(cls, lang_code: str) -> bool:
        return lang_code in cls.INDIC_LANGUAGES

    @classmethod
    def get_language_name(cls, lang_code: str) -> str:
        if lang_code == "en":
            return "English"
        return cls.INDIC_LANGUAGES.get(lang_code, f"Unknown ({lang_code})")
