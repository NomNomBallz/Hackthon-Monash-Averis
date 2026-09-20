# MEMBER 5's Code (Danny) — audit trail.
# Append-only. Shipping is dispute-prone: six months later someone asks why a
# bill of lading was cleared, and "the AI said so" is not an answer.

import json
import os
from datetime import datetime, timezone

TRAIL_PATH = os.path.join("outputs", "audit_trail.jsonl")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record(email_id, action, detail, *, actor="system", source=None,
           model=None, confidence=None, path=TRAIL_PATH):
    """action: classified | extracted | compared | escalated | reviewed | failed"""
    entry = {"at": _now(), "email_id": email_id, "actor": actor,
             "action": action, "detail": detail}
    if source:
        entry["source"] = source
    if model:
        entry["model"] = model
    if confidence is not None:
        entry["confidence"] = round(float(confidence), 3)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read(email_id=None, path=TRAIL_PATH):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if email_id is None or entry.get("email_id") == email_id:
                out.append(entry)
    return out


def from_result(result):
    """Synthesise entries for results processed before the trail existed,
    so the UI is never blank. Written entries always take precedence."""
    eid = result.get("email_id", "")
    at = result.get("processed_at", _now())
    entries = [{"at": at, "email_id": eid, "actor": "system", "action": "classified",
                "detail": f"Classified as {result.get('category')} by "
                          f"{'subject rule' if result.get('decided_by') == 'rule' else 'language model'}"}]
    for name, f in (result.get("fields") or {}).items():
        conf = f.get("si_confidence")
        if f.get("match") is False or (conf is not None and conf < 0.70):
            entries.append({"at": at, "email_id": eid, "actor": "system",
                            "action": "extracted",
                            "detail": f"Read {name} as \u201c{f.get('si_raw')}\u201d / \u201c{f.get('bl_raw')}\u201d",
                            "source": f.get("si_source"), "model": f.get("model"),
                            "confidence": conf})
    if result.get("error"):
        entries.append({"at": at, "email_id": eid, "actor": "system",
                        "action": "failed", "detail": result["error"]})
    elif result.get("review_reason"):
        entries.append({"at": at, "email_id": eid, "actor": "system",
                        "action": "escalated",
                        "detail": (result.get("escalation") or {}).get("evidence")
                                  or result["review_reason"]})
    else:
        entries.append({"at": at, "email_id": eid, "actor": "system",
                        "action": "compared",
                        "detail": f"Compared seven fields \u2014 {result.get('status')}"})
    return entries
