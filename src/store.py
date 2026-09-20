# MEMBER 5's Code (Danny) — data access.
# Merges: data_v2/inbox (raw emails) + outputs/results.json (pipeline)
#         + outputs/reviews.json (human decisions).
# Makes no AI calls, so running the console costs no tokens.

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import escalation

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data_v2"
OUT = ROOT / "outputs"

RESULTS_PATH = OUT / "results.json"
REVIEWS_PATH = OUT / "reviews.json"
SUBMISSION_PATH = OUT / "submission.json"

FIELDS = ["shipper", "consignee", "notify_party", "port_of_loading",
          "port_of_discharge", "container_count", "gross_weight_kg"]

FIELD_LABELS = {
    "shipper": "Shipper", "consignee": "Consignee", "notify_party": "Notify party",
    "port_of_loading": "Port of loading", "port_of_discharge": "Port of discharge",
    "container_count": "Container count", "gross_weight_kg": "Gross weight",
}
CATEGORY_LABELS = {
    "BL_COMPARISON": "Document comparison", "SI_REQUEST": "New SI request",
    "INVOICE_QUERY": "Invoice query", "GENERAL": "General", "SPAM": "Spam",
    None: "Not classified",
}
REASON_LABELS = escalation.REASONS


def _load(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_inbox():
    d = DATA / "inbox"
    if not d.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(d.glob("email_*.json"))]


def read_attachment(rel_path):
    """Plain text only. Binary formats belong to the extractor."""
    p = DATA / rel_path
    if not p.exists() or p.suffix.lower() != ".txt":
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def pipeline_has_run():
    return RESULTS_PATH.exists()


def load_cases():
    results = _load(RESULTS_PATH, {})
    reviews = _load(REVIEWS_PATH, {})
    cases = []
    for email in read_inbox():
        eid = email["email_id"]
        c = dict(results.get(eid, {}))
        c["email_id"] = eid
        c["subject"] = email.get("subject", "")
        c["from"] = email.get("from", "")
        c["attachments"] = email.get("attachments", [])
        c.setdefault("category", None)
        c.setdefault("decided_by", None)
        c.setdefault("status", "PENDING")
        c.setdefault("review_reason", None)
        c.setdefault("has_defect", False)
        c.setdefault("defect_fields", [])
        c.setdefault("fields", {})
        c.setdefault("error", None)
        decision = reviews.get(eid)
        if decision:
            c = escalation.apply_decision(c, decision["decision"],
                                          decision.get("reviewer", "reviewer"))
            c["reviewed_at"] = decision.get("at")
            c["reviewer_note"] = decision.get("note")
        cases.append(c)
    return cases


def save_decision(email_id, decision, reviewer="reviewer", note=None):
    reviews = _load(REVIEWS_PATH, {})
    reviews[email_id] = {
        "decision": decision, "reviewer": reviewer, "note": note,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _save(REVIEWS_PATH, reviews)


def clear_decision(email_id):
    reviews = _load(REVIEWS_PATH, {})
    reviews.pop(email_id, None)
    _save(REVIEWS_PATH, reviews)


def export_submission(cases):
    """The file the scorer reads, carrying every human decision."""
    submission = {}
    for c in cases:
        status = c["status"]
        if status in ("PENDING", "FAILED"):
            status = "NEEDS_REVIEW"
        submission[c["email_id"]] = {
            "category": c.get("category") or "GENERAL",
            "status": status,
            "review_reason": c.get("review_reason"),
            "has_defect": bool(c.get("has_defect")),
            "defect_fields": c.get("defect_fields", []),
        }
    _save(SUBMISSION_PATH, submission)
    return len(submission)


def summary(cases):
    by_status, by_category, by_reason = {}, {}, {}
    for c in cases:
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1
        if c.get("category"):
            by_category[c["category"]] = by_category.get(c["category"], 0) + 1
        if c.get("review_reason"):
            by_reason[c["review_reason"]] = by_reason.get(c["review_reason"], 0) + 1
    return {"total": len(cases), "by_status": by_status,
            "by_category": by_category, "by_reason": by_reason,
            "reviewed": sum(1 for c in cases if c.get("reviewed_by"))}
