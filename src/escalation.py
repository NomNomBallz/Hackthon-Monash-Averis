# MEMBER 5's Code (Danny) — human-in-the-loop escalation
#
# Decides WHEN the pipeline must stop and ask a person, instead of guessing.
# One rule above all others:
#     A blank value is NEEDS_REVIEW, never MISMATCH.
# "???" means "I don't know", not "these disagree".

from typing import Optional, Any

BLANK_MARKERS = {"???", "____", "_____", "______", "TBA", "TBC", "N/A", "NA",
                 "-", "--", "", "____MT", "PENDING"}
CONFIDENCE_THRESHOLD = 0.70
BL_SIGNALS = ("BILL OF LADING", "B/L", "SHIPPED ON BOARD", "PORT OF LOADING",
              "PORT OF DISCHARGE", "CONTAINER", "POL", "POD")

REASONS = {
    "missing_attachment": "An attachment is missing",
    "unreadable":         "A document could not be read",
    "wrong_doc_type":     "The wrong document type was attached",
    "missing_value":      "A required value is blank in the document",
}


def is_blank(value: Any) -> bool:
    """True when the DOCUMENT left this empty, not when we failed to read it."""
    if value is None:
        return True
    return str(value).strip().upper().replace(" ", "") in \
        {m.replace(" ", "") for m in BLANK_MARKERS}


def looks_like_bill_of_lading(text: Optional[str]) -> bool:
    if not text:
        return False
    upper = text.upper()
    if "COMMERCIAL INVOICE" in upper or "PACKING LIST" in upper:
        return False
    return sum(1 for s in BL_SIGNALS if s in upper) >= 2


def check(email, si, bl, si_text=None, bl_text=None, confidences=None):
    """None when decidable automatically, else {reason, field, evidence}."""
    attachments = email.get("attachments") or []

    if len(attachments) < 2:
        return {"reason": "missing_attachment", "field": None,
                "evidence": f"{email['email_id']} asks for a document check but carries "
                            f"{len(attachments)} attachment(s). Both an SI and a BL are needed."}

    for text, path in ((si_text, attachments[0]), (bl_text, attachments[1])):
        if text is not None and len(text.strip()) < 40:
            return {"reason": "unreadable", "field": None,
                    "evidence": f"{path} produced {len(text.strip())} characters of text. "
                                f"It is most likely a scanned image with no text layer."}

    if si is None or bl is None:
        missing = "SI" if si is None else "BL"
        return {"reason": "unreadable", "field": None,
                "evidence": f"The {missing} document could not be parsed into fields."}

    if bl_text and not looks_like_bill_of_lading(bl_text):
        head = bl_text.strip().splitlines()[0][:60] if bl_text.strip() else "(empty)"
        return {"reason": "wrong_doc_type", "field": None,
                "evidence": f"{attachments[1]} is headed \u201c{head}\u201d and carries no port, "
                            f"container or weight fields. It is not a bill of lading."}

    for field in ("shipper", "consignee", "notify_party", "port_of_loading",
                  "port_of_discharge", "container_count", "gross_weight_kg"):
        si_val, bl_val = si.get(field), bl.get(field)
        if is_blank(si_val) or is_blank(bl_val):
            side = "SI" if is_blank(si_val) else "BL"
            other = bl_val if side == "SI" else si_val
            return {"reason": "missing_value", "field": field,
                    "evidence": f"{field} is blank in the {side}. The other document states "
                                f"\u201c{other}\u201d. A blank is uncertainty, not a discrepancy, "
                                f"so nothing was flagged."}

    if confidences:
        worst_field = min(confidences, key=confidences.get)
        worst = confidences[worst_field]
        if worst < CONFIDENCE_THRESHOLD:
            return {"reason": "unreadable", "field": worst_field,
                    "evidence": f"{worst_field} was read at {worst:.2f} confidence, below the "
                                f"{CONFIDENCE_THRESHOLD:.2f} threshold. Comparing on it would "
                                f"risk a false alarm."}
    return None


def apply_decision(result, decision, reviewer="reviewer"):
    """Fold a human decision back into the result so the submission reflects it.
    A review that does not change the output is decoration."""
    if decision == "MISMATCH":
        result["status"] = "MISMATCH"
        result["has_defect"] = True
        result["review_reason"] = None
        if not result.get("defect_fields"):
            flagged = (result.get("escalation") or {}).get("field")
            result["defect_fields"] = [flagged] if flagged else []
    elif decision == "OK":
        result["status"] = "OK"
        result["has_defect"] = False
        result["defect_fields"] = []
        result["review_reason"] = None
    elif decision == "NEEDS_REVIEW":
        result["status"] = "NEEDS_REVIEW"
        result["has_defect"] = False
        result["defect_fields"] = []
    result["reviewed_by"] = reviewer
    return result
