import os
import json
from dotenv import load_dotenv
from loader import Inbox

# Stage 1: Classifier (Ryan)
from src.classifier import EmailClassifier

# Stage 2: Extractor high-level orchestrator (Jayvan)
from src.extractor import extract_si_bl_pair

# Stage 3: Comparator (Barry - unmodified)
from src.comparator import compare_documents

load_dotenv()

classifier = EmailClassifier()

REQUIRED_KEYS = [
    "shipper", "consignee", "notify_party", 
    "port_of_loading", "port_of_discharge", 
    "container_count", "gross_weight_kg"
]
PLACEHOLDERS = {"TBA", "???", "_______", "NONE", "NULL", "N/A", "NA", ""}


def find_missing_keys(si_dict: dict, bl_dict: dict) -> list[str]:
    """Diagnostics to see which fields triggered missing_value."""
    def is_bad(val):
        if val is None:
            return True
        return str(val).strip().upper() in PLACEHOLDERS

    reasons = []
    si_clean = {str(k).strip().lower(): v for k, v in (si_dict or {}).items()}
    bl_clean = {str(k).strip().lower(): v for k, v in (bl_dict or {}).items()}

    for k in REQUIRED_KEYS:
        si_val = si_clean.get(k)
        bl_val = bl_clean.get(k)

        if k not in si_clean or is_bad(si_val):
            reasons.append(f"SI missing or placeholder for '{k}' (got: {repr(si_val)})")
        if k not in bl_clean or is_bad(bl_val):
            reasons.append(f"BL missing or placeholder for '{k}' (got: {repr(bl_val)})")

    return reasons


def resolve_attachment_path(attachment_name: str, inbox: Inbox) -> str:
    """
    Ensures local file existence for Jayvan's parser (.xlsx, .pdf, .docx).
    Checks local disk first; otherwise downloads via inbox.read_bytes().
    """
    candidates = [
        attachment_name,
        os.path.join("data_v2", attachment_name),
        os.path.join("data_v2", "attachments", os.path.basename(attachment_name)),
        os.path.join("attachments", os.path.basename(attachment_name))
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    # If running purely against Docker remote server without local files, cache to disk
    os.makedirs("temp_attachments", exist_ok=True)
    local_target = os.path.join("temp_attachments", os.path.basename(attachment_name))
    if not os.path.exists(local_target):
        raw_bytes = inbox.read_bytes(attachment_name)
        with open(local_target, "wb") as f:
            f.write(raw_bytes)
    return local_target


def separate_attachments(attachments: list) -> tuple[str | None, str | None]:
    si_att = next((a for a in attachments if "_SI" in a.upper() or "SI." in a.upper()), None)
    bl_att = next((a for a in attachments if "_BL" in a.upper() or "BL." in a.upper()), None)
    
    if not si_att and len(attachments) >= 1:
        si_att = attachments[0]
    if not bl_att and len(attachments) >= 2:
        bl_att = attachments[1]
        
    return si_att, bl_att


def process_email(inbox: Inbox, email: dict) -> dict:
    email_id = email.get("email_id")
    category = classifier.classify_single(email)
    
    # -------------------------------------------------------------
    # STAGE 1: Triage Short-Circuit
    # -------------------------------------------------------------
    if category != "BL_COMPARISON":
        return {
            "category": category,
            "status": None,
            "review_reason": None,
            "has_defect": None,
            "defect_fields": []
        }

    # -------------------------------------------------------------
    # STAGE 2: Attachment Verification & Extraction via extract_si_bl_pair
    # -------------------------------------------------------------
    attachments = email.get("attachments", [])
    if len(attachments) < 2:
        return compare_documents({
            "SI": None,
            "BL": None
        })

    si_file, bl_file = separate_attachments(attachments)
    if not si_file or not bl_file:
        return compare_documents({
            "SI": None if not si_file else {},
            "BL": None if not bl_file else {}
        })

    try:
        # Resolve physical file path so Excel/PDF/Word parsers work
        si_path = resolve_attachment_path(si_file, inbox)
        bl_path = resolve_attachment_path(bl_file, inbox)

        # Call Jayvan's full multi-format extractor
        extraction_res = extract_si_bl_pair(si_path, bl_path)
    except Exception as e:
        print(f"[{email_id}] Extraction exception: {e}")
        extraction_res = {"status": "UNREADABLE", "error": str(e)}

    # Handle unreadable/OCR error cases
    if extraction_res.get("status") != "SUCCESS":
        return compare_documents({
            "SI": {"Error": "OCR Scan Failed - Unreadable characters %^&*"},
            "BL": {"Error": "OCR Scan Failed - Unreadable characters %^&*"}
        })

    # Pydantic or dict normalization
    si_data = extraction_res.get("si_data")
    bl_data = extraction_res.get("bl_data")

    if hasattr(si_data, "model_dump"):
        si_dict = si_data.model_dump()
    else:
        si_dict = si_data or {}

    if hasattr(bl_data, "model_dump"):
        bl_dict = bl_data.model_dump()
    else:
        bl_dict = bl_data or {}

    payload_for_barry = {
        "SI": si_dict,
        "BL": bl_dict
    }

    # -------------------------------------------------------------
    # STAGE 3: Comparator (Barry)
    # -------------------------------------------------------------
    result = compare_documents(payload_for_barry)
    result["category"] = "BL_COMPARISON"

    # Missing value diagnosis log
    if result.get("review_reason") == "missing_value":
        culprits = find_missing_keys(si_dict, bl_dict)
        print(f"\n🔍 [DEBUG {email_id}] Triggered 'missing_value' because:")
        for c in culprits:
            print(f"   👉 {c}")
        print()

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("🚢 RUNNING COMPLETE END-TO-END SUBMISSION RUN")
    print("=" * 60)

    # 1. Connect to Docker inbox
    inbox = Inbox("http://localhost:8080")
    emails = inbox.emails()
    total_emails = len(emails)
    print(f"📥 Loaded {total_emails} emails from inbox.\n")

    submission = {}

    # 2. Process every email
    for idx, email in enumerate(emails, 1):
        email_id = email.get("email_id")
        print(f"[{idx}/{total_emails}] Processing {email_id}...", end=" ", flush=True)

        try:
            result = process_email(inbox, email)
            submission[email_id] = result
            status_summary = result.get("status") or result.get("category")
            print(f"-> {status_summary}")
        except Exception as err:
            print(f"-> ERROR ({err})")
            # Safe fallback so submission format remains intact
            submission[email_id] = {
                "category": "GENERAL",
                "status": None,
                "review_reason": None,
                "has_defect": None,
                "defect_fields": []
            }

    # 3. Save artifact locally to submission.json
    output_path = "submission.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(submission, f, indent=2)
    print(f"\n💾 Saved full predictions to {output_path} ({len(submission)} entries).")

    # 4. Post submission to the Docker grading endpoint
    print("\n📤 Posting results to evaluation server...")
    try:
        score_report = inbox.submit(submission)
        print("\n" + "=" * 60)
        print("🏆 EVALUATION SCORE REPORT")
        print("=" * 60)
        print(json.dumps(score_report, indent=2))
        print("=" * 60)
    except Exception as err:
        print(f"❌ Server submission failed: {err}")