"""Lightweight red-flag detection, applied before the model answers.

This is a deterministic safety net, independent of the model: if the user's
message mentions a possible emergency, the API flags it so every client can
show an emergency banner, whatever the model says.
"""
import re

EMERGENCY_NOTICE = (
    "Some of what you describe can be a medical emergency. If symptoms are severe or "
    "sudden, call your local emergency number now (112 in India, 911 in the US)."
)

_RED_FLAGS = re.compile(
    r"chest pain|crushing chest|heart attack"
    r"|can'?t breathe|cannot breathe|difficulty breathing|struggling to breathe|not breathing"
    r"|suicid|kill myself|end my life|self[- ]?harm|want to die"
    r"|stroke|face (is )?drooping|slurred speech|sudden (numbness|weakness)"
    r"|unconscious|unresponsive|passed out|seizure|convulsion"
    r"|severe bleeding|bleeding heavily|won'?t stop bleeding|coughing (up )?blood|vomiting blood"
    r"|overdos|poison|anaphyla|throat (is )?swelling",
    re.IGNORECASE,
)


def detect_emergency(text: str) -> bool:
    return bool(text and _RED_FLAGS.search(text))
