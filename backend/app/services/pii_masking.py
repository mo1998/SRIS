"""PII masking for candidate content sent to LLM providers.

Candidate answers are redacted before they reach any evaluation provider
(especially cloud). The reference copy stays untouched in the database; only
the payload is masked. Masking is fail-closed: any masking error propagates so
the caller falls back instead of sending potentially unmasked PII.

Names are handled conservatively: only the candidate's own name (from the
response record) is redacted. Arbitrary third-party names are not detected;
documenting that limitation beats a heuristic that mutilates ordinary text.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# ASCII + Arabic-Indic digits, so Arabic phone numbers are covered too.
_D = r"[0-9\u0660-\u0669]"
PHONE_RE = re.compile(
    rf"(?:\+?{_D}[\s.-]?)?(?:\(?{_D}{{3}}\)?[\s.-]?)?{_D}{{3}}[\s.-]?{_D}{{4}}\b"
)

EMAIL_TOKEN = "[EMAIL]"
PHONE_TOKEN = "[PHONE]"
NAME_TOKEN = "[NAME]"


@dataclass
class MaskingSummary:
    masked: bool = False
    emails: int = 0
    phones: int = 0
    names: int = 0

    def to_dict(self) -> dict:
        return {
            "masked": self.masked,
            "emails": self.emails,
            "phones": self.phones,
            "names": self.names,
        }


def _redact(text: str, pattern: re.Pattern, token: str) -> Tuple[str, int]:
    masked_text, count = pattern.subn(token, text or "")
    return masked_text, count


def _redact_names(text: str, candidate_name: Optional[str]) -> Tuple[str, int]:
    if not candidate_name or not text:
        return text, 0
    total = 0
    for token in re.split(r"[\s,.;:]+", candidate_name.strip()):
        token = token.strip("'\"()[]")
        if len(token) >= 3 and not re.fullmatch(rf"{_D}+", token):
            pattern = re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE)
            text, count = pattern.subn(NAME_TOKEN, text)
            total += count
    return text, total


def mask_pii(text: str, candidate_name: Optional[str] = None) -> Tuple[str, MaskingSummary]:
    """Redact emails, phone-like patterns, and the candidate's own name.

    Returns (masked_text, summary). Raises on unexpected masking errors so the
    caller can fail closed (never forward unmasked PII).
    """
    masked_text = text or ""
    summary = MaskingSummary()

    masked_text, count = _redact(masked_text, EMAIL_RE, EMAIL_TOKEN)
    summary.emails = count

    masked_text, count = _redact(masked_text, PHONE_RE, PHONE_TOKEN)
    summary.phones = count

    masked_text, count = _redact_names(masked_text, candidate_name)
    summary.names = count

    summary.masked = bool(summary.emails or summary.phones or summary.names)
    return masked_text, summary