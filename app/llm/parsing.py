"""Tolerant JSON-object extraction shared by the graph nodes and the hive."""
from __future__ import annotations

import json
import re
from typing import Optional


def parse_json(text: str) -> Optional[dict]:
    """Extract the first JSON object from model output.

    Models routinely wrap JSON in prose or code fences, so a bare json.loads
    on the whole reply is brittle. Try, in order: the full reply, each code
    fence, then the outermost { ... } span. Returns None when nothing parses
    to a dict.
    """
    if not text:
        return None
    text = text.strip()
    candidates = [text, *re.findall(r"```(?:json)?\s*(.*?)```", text, re.S)]
    for cand in candidates:
        try:
            v = json.loads(cand)
            if isinstance(v, dict):
                return v
        except Exception:
            pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            v = json.loads(m.group(0))
            return v if isinstance(v, dict) else None
        except Exception:
            return None
    return None
