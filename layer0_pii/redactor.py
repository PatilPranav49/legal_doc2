"""
layer0_pii/redactor.py — PII Detection & Redaction for Indian Legal Documents

Privacy-first: redacts all detected PII BEFORE any text leaves the device
(i.e., before sending to Sarvam API or any other external service).

After translation, call redactor.restore() to put original PII values back
into the translated English text.

Patterns are conservative — only match with strong contextual signals to avoid
false positives on section numbers, case numbers, dates, and normal text.
"""

import re
from dataclasses import dataclass, field
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PIIMatch:
    pii_type: str
    original: str
    placeholder: str   # unique indexed placeholder e.g. [AADHAAR_1]


@dataclass
class RedactionResult:
    original_text: str
    redacted_text: str
    pii_found: list
    pii_matches: list
    pii_count: int
    restoration_map: dict = field(default_factory=dict)
    # restoration_map: { "[AADHAAR_1]": "2345 6789 0123", ... }


# ── PII Pattern Definitions ────────────────────────────────────────────────────
# Each tuple: (name, regex_pattern)
# Placeholders are now generated dynamically with an index per match.

PII_PATTERNS = [
    # ── Aadhaar: XXXX XXXX XXXX — first digit 2-9 (real Aadhaar never starts with 0/1)
    (
        "AADHAAR",
        r"\b[2-9][0-9]{3}[\s\-][0-9]{4}[\s\-][0-9]{4}\b",
    ),

    # ── PAN: exactly 5 letters + 4 digits + 1 letter (ABCDE1234F format)
    (
        "PAN",
        r"(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z0-9])",
    ),

    # ── IFSC: 4 letters + '0' + 6 alphanumeric — strict format
    (
        "IFSC",
        r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    ),

    # ── Indian mobile numbers: 10 digits starting 6-9, optional +91/91/0 prefix
    (
        "PHONE",
        r"(?<!\d)(\+91[\s\-]?|91[\s\-]?|0)?[6-9][0-9]{9}(?!\d)",
    ),

    # ── Email addresses
    (
        "EMAIL",
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    ),

    # ── Bank account numbers — ONLY when preceded by explicit keyword
    (
        "BANK_ACCOUNT",
        r"(?:account\s*(?:no\.?|number|num\.?|#)\s*[:\-]?\s*)([0-9]{9,18})\b",
    ),

    # ── Amounts with ₹ symbol — requires the rupee symbol to avoid false positives
    (
        "AMOUNT",
        r"₹\s?[0-9,]+(?:\.[0-9]{1,2})?(?:\s?(?:lakh|crore|thousand|lac)s?)?",
    ),

    # ── Passport: letter + 7 digits — ONLY when keyword present
    (
        "PASSPORT",
        r"(?:passport\s*(?:no\.?|number)?\s*[:\-]?\s*)([A-Z][0-9]{7})\b",
    ),

    # ── Voter ID: VoterID/EPIC format (optional keyword)
    (
        "VOTER_ID",
        r"(?:voter\s*(?:id|card|no\.?)\s*[:\-]?\s*)?(?<![A-Z])([A-Z]{3}[0-9]{7})(?![A-Z0-9])",
    ),
]

COMPILED_PATTERNS = [
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in PII_PATTERNS
]


class PIIRedactor:
    """
    Detects and redacts Indian PII from text before it is sent to any external API.
    Uses unique indexed placeholders (e.g. [AADHAAR_1], [PHONE_2]) so that
    restore() can unambiguously put original values back after translation.
    """

    def redact(self, text: str) -> RedactionResult:
        if not text or not text.strip():
            return RedactionResult(
                original_text=text, redacted_text=text,
                pii_found=[], pii_matches=[], pii_count=0,
                restoration_map={}
            )

        redacted = text
        all_matches: list[PIIMatch] = []
        pii_types_found: set[str] = set()
        restoration_map: dict[str, str] = {}

        # Track per-type counter for unique placeholders
        type_counters: dict[str, int] = {}

        for pii_type, pattern in COMPILED_PATTERNS:
            # Find all matches in current (already partially redacted) text
            found = list(pattern.finditer(redacted))
            if not found:
                continue

            pii_types_found.add(pii_type)

            # Replace each match individually so we get unique placeholders
            # Work right-to-left to preserve offsets
            for m in reversed(found):
                type_counters[pii_type] = type_counters.get(pii_type, 0) + 1
                idx = type_counters[pii_type]
                placeholder = f"[{pii_type}_{idx}]"

                original_value = m.group()
                restoration_map[placeholder] = original_value

                all_matches.append(PIIMatch(pii_type, original_value, placeholder))
                redacted = redacted[:m.start()] + placeholder + redacted[m.end():]

        pii_types_list = sorted(pii_types_found)

        if pii_types_list:
            counts = {}
            for m in all_matches:
                counts[m.pii_type] = counts.get(m.pii_type, 0) + 1
            logger.info(f"PII redacted: {counts}")
        else:
            logger.info("No PII detected.")

        return RedactionResult(
            original_text=text,
            redacted_text=redacted,
            pii_found=pii_types_list,
            pii_matches=all_matches,
            pii_count=len(all_matches),
            restoration_map=restoration_map,
        )

    def restore(self, text: str, result: RedactionResult) -> str:
        """
        Replace all indexed placeholders in `text` with their original PII values.
        Safe to call on the translated English text after translation.

        Example:
            redacted:   "Phone: [PHONE_1], Aadhaar: [AADHAAR_1]"
            translated: "Phone: [PHONE_1], Aadhaar: [AADHAAR_1]"   (placeholders survive)
            restored:   "Phone: 9876543210, Aadhaar: 2345 6789 0123"
        """
        if not result.restoration_map or not text:
            return text

        restored = text
        for placeholder, original in result.restoration_map.items():
            restored = restored.replace(placeholder, original)

        return restored

    def get_pii_summary(self, result: RedactionResult) -> str:
        if not result.pii_found:
            return "No sensitive data detected."
        counts = {}
        for m in result.pii_matches:
            counts[m.pii_type] = counts.get(m.pii_type, 0) + 1
        lines = ["⚠️ Sensitive data detected and redacted:"]
        for pii_type, count in sorted(counts.items()):
            lines.append(f"  • {pii_type}: {count} instance(s)")
        lines.append("✅ All PII redacted before sending to any external API.")
        return "\n".join(lines)