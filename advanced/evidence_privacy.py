"""Targeted email redaction for synthetic native evidence, not a PII guarantee."""

import re
from typing import Any

_EMAIL = re.compile(r"[\w.!#$%&'*+=?^`{|}~-]+@(?:[\w-]+\.)*[\w-]+", re.UNICODE)


def redact_emails(value: Any) -> Any:
    """Return a JSON-shaped copy with email-like strings redacted at every depth.

    Keep numeric counters, event identities and tool pairs unchanged. This does
    not detect obfuscated addresses or other classes of personal information.
    Call before serialization, so JSON Unicode escaping cannot hide an address.
    """
    if isinstance(value, str):
        return _EMAIL.sub("[REDACTED_EMAIL]", value)
    if isinstance(value, list):
        return [redact_emails(item) for item in value]
    if isinstance(value, dict):
        return {redact_emails(key): redact_emails(item) for key, item in value.items()}
    return value
