import re

_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    # PAN card numbers (e.g. ABCDE1234F)
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN]"),
    # Aadhaar-like 12-digit numbers with optional spaces
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[ID_NUMBER]"),
    # Email addresses
    (re.compile(r"\b[\w.-]+@[\w.-]+\.\w{2,}\b", re.IGNORECASE), "[EMAIL]"),
    # Phone numbers — Indian (+91) and international formats
    (
        re.compile(
            r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
        ),
        "[PHONE]",
    ),
]


def scrub_pii(text: str) -> str:
    """Remove PII patterns from review text."""
    if not text:
        return text
    result = text
    for pattern, replacement in _PII_PATTERNS:
        result = pattern.sub(replacement, result)
    return result
