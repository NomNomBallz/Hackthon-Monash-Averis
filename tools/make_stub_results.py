# DEV STUB — delete once the real pipeline writes outputs/results.json.
# Produces results.json in the agreed contract shape so the console can be
# built and demoed before the classifier, extractor and comparator land.
# Plain-text attachments only, no AI calls, costs nothing to run.
#   python3 tools/make_stub_results.py

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import escalation, store  # noqa: E402

LABEL_MAP = {
    "shipper": ["shipper", "shipper/exporter", "shipper / exporter"],
    "consignee": ["consignee", "consignee (non-negotiable)", "to the order of"],
    "notify_party": ["notify", "notify party", "notify address"],
    "port_of_loading": ["port of loading", "port of loading (pol)", "load port",
                        "pol", "port of receipt"],
    "port_of_discharge": ["port of discharge", "port of discharge (pod)", "pod",
                          "discharge port", "destination port"],
    "container_count": ["container count", "total containers", "no. of containers",
                        "no. of containers or packages", "number of containers"],
    "gross_weight_kg": ["gross weight (kg)", "gross wt (kgs)", "gross weight",
                        "gross weight\u6bdb\u91cd(kgs)", "total gross weight"],
}
LOOKUP = {syn: field for field, syns in LABEL_MAP.items() for syn in syns}


def classify(subject):
    """Subject only. Matching the body misreads every SI request as a comparison."""
    s = re.sub(r"^(RE_|RE:|FW_|FWD_|FW:)\s*", "", subject.upper()).strip()
    if s.startswith("_RPA_") or "PROCESS COMPLETED" in s:
        return "GENERAL", "rule"
    if any(p in s for p in ["UPDATE SUMMARY", "BERTHING", "DELIVERY PLANNING",
                            "_REMINDER_", "HOLIDAY", "NOTICE"]):
        return "GENERAL", "rule"
    if any(p in s for p in ["BILLING", "MISSING GR", "CANCEL INVOICE", "TOTAL FREIGHT",
                            "LOCAL CHARGES", "TELEX RELEASE", "D & D", "DEMURRAGE",
                            "DETENTION", "INVOICE"]):
        return "INVOICE_QUERY", "rule"
    if any(p in s for p in ["CUST SI", "REQUEST SI", "SI NEEDED", "SI -", "SUBMIT SI"]):
        return "SI_REQUEST", "rule"
    if any(p in s for p in ["TO CONFIRM DOCS", "REQUEST BL DRAFT", "DRAFT BL", "CONFIRM DOC"]):
        return "BL_COMPARISON", "rule"
    if re.match(r"^AF[A-Z]{1,4} - |^AIE - ", s):
        return "BL_COMPARISON", "rule"
    if re.search(r"\([A-Z]{3,4}[A-Z0-9]{6,}\)", s) and " - " in s:
        return "BL_COMPARISON", "rule"
    return "GENERAL", "llm"


def parse(text):
    found = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        if ":" not in line:
            continue
        label, _, value = line.partition(":")
        key = LOOKUP.get(label.strip().lower())
        if key and key not in found:
            found[key] = {"raw": value.strip(), "label": label.strip(), "line": lineno}
    return found


def normalise(key, raw):
    if raw is None or escalation.is_blank(raw):
        return None
    s = str(raw).strip()
    if key == "container_count":
        nums = re.findall(r"(\d+)\s*[xX]\s*\d", s) or re.findall(r"^\s*(\d+)", s)
        return sum(int(n) for n in nums) if nums else None
    if key == "gross_weight_kg":
        m = re.search(r"([\d,]+(?:\.\d+)?)", s)
        if not m:
            return None
        v = float(m.group(1).replace(",", ""))
        if re.search(r"\bMT\b|TONNE", s, re.I):
            v *= 1000
        if re.search(r"\bLBS?\b|POUND", s, re.I):
            v *= 0.453592
        return round(v, 2)
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def build():
    results = {}
    for email in store.read_inbox():
        eid = email["email_id"]
        category, decided_by = classify(email.get("subject", ""))
        rec = {"category": category, "decided_by": decided_by, "status": "OK",
               "review_reason": None, "has_defect": False, "defect_fields": [],
               "fields": {}, "error": None, "escalation": None,
               "processed_at": "2026-09-21T09:14:26Z"}

        atts = email.get("attachments") or []
        if category != "BL_COMPARISON" or len(atts) < 2:
            results[eid] = rec
            continue

        si_text = store.read_attachment(atts[0])
        bl_text = store.read_attachment(atts[1])
        if si_text is None or bl_text is None:
            rec["status"] = "NEEDS_REVIEW"
            rec["review_reason"] = "unreadable"
            rec["escalation"] = {"reason": "unreadable", "field": None,
                                 "evidence": f"{atts[1]} is not a plain-text file; "
                                             f"the real extractor handles this format."}
            results[eid] = rec
            continue

        si, bl = parse(si_text), parse(bl_text)
        defects = []
        for key in store.FIELDS:
            a, b = si.get(key, {}), bl.get(key, {})
            na, nb = normalise(key, a.get("raw")), normalise(key, b.get("raw"))
            match = (na is not None and nb is not None and na == nb)
            rec["fields"][key] = {
                "si_value": na, "bl_value": nb,
                "si_raw": a.get("raw"), "bl_raw": b.get("raw"),
                "si_label": a.get("label", key), "bl_label": b.get("label", key),
                "si_source": f"{Path(atts[0]).name}:{a.get('line', '')}",
                "bl_source": f"{Path(atts[1]).name}:{b.get('line', '')}",
                "si_confidence": 0.97 if a else 0.10,
                "bl_confidence": 0.97 if b else 0.10,
                "model": "stub-regex", "match": match,
            }
            if not match and na is not None and nb is not None:
                defects.append(key)

        flag = escalation.check(email,
                                {k: v.get("raw") for k, v in si.items()},
                                {k: v.get("raw") for k, v in bl.items()},
                                si_text, bl_text)
        if flag:
            rec["status"] = "NEEDS_REVIEW"
            rec["review_reason"] = flag["reason"]
            rec["escalation"] = flag
        elif defects:
            rec["status"] = "MISMATCH"
            rec["has_defect"] = True
            rec["defect_fields"] = defects
        results[eid] = rec

    store.OUT.mkdir(parents=True, exist_ok=True)
    store.RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                                  encoding="utf-8")
    counts = {}
    for r in results.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"wrote {len(results)} results -> {store.RESULTS_PATH}")
    print(counts)


if __name__ == "__main__":
    build()
