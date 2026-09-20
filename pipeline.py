import os
import json
from dotenv import load_dotenv
from loader import Inbox

# Stage 1: Classifier (Ryan)
from src.classifier import EmailClassifier

# Stage 2: Extractor (Jayvan)
from src.extractor.extractor import (
    DocumentPairExtraction,
    extract_pair_with_groq,
    extract_pair_with_vision_gemini
)

# Stage 3: Comparator (Barry)
from src.comparator import compare_documents

load_dotenv()

# Initialize Stage 1 Classifier
classifier = EmailClassifier()


def separate_attachments(attachments: list) -> tuple[str | None, str | None]:
    """Identify SI and BL attachments by filename convention."""
    si_att = next((a for a in attachments if "_SI" in a.upper() or "SI." in a.upper()), None)
    bl_att = next((a for a in attachments if "_BL" in a.upper() or "BL." in a.upper()), None)
    
    # Fallback by index if filenames don't contain standard tags
    if not si_att and len(attachments) >= 1:
        si_att = attachments[0]
    if not bl_att and len(attachments) >= 2:
        bl_att = attachments[1]
        
    return si_att, bl_att


def process_email(inbox: Inbox, email: dict) -> dict:
    """
    Orchestrates the 3-stage lifecycle for an email:
    Stage 1: Triage -> Stage 2: Extraction -> Stage 3: Verification
    """
    email_id = email.get("email_id")
    
    # -------------------------------------------------------------
    # STAGE 1: Email Triage (Classifier)
    # -------------------------------------------------------------
    category = classifier.classify_single(email)
    
    # Short-circuit non-BL comparison emails (Save tokens & time)
    if category != "BL_COMPARISON":
        return {
            "category": category,
            "status": None,
            "review_reason": None,
            "has_defect": None,
            "defect_fields": []
        }

    # -------------------------------------------------------------
    # STAGE 2: Extraction (Jayvan)
    # -------------------------------------------------------------
    attachments = email.get("attachments", [])
    si_file, bl_file = separate_attachments(attachments)

    # Edge Case: Missing attachment
    if not si_file or not bl_file:
        missing_payload = {
            "SI": None if not si_file else {},
            "BL": None if not bl_file else {}
        }
        return compare_documents(missing_payload)

    # Ingest document text
    try:
        si_text = inbox.read_text(si_file)
    except Exception:
        si_text = ""

    try:
        bl_text = inbox.read_text(bl_file)
    except Exception:
        bl_text = ""

    extracted_pair = None

    # Step 2A: Fast digital text extraction via Groq
    if len(si_text.strip()) > 50 and len(bl_text.strip()) > 50:
        try:
            extracted_pair = extract_pair_with_groq(si_text, bl_text)
        except Exception as e:
            print(f"[{email_id}] Groq digital extraction failed ({e}). Trying Gemini Vision...")

    # Step 2B: Fallback to Gemini Multimodal Vision for scans/images
    if not extracted_pair:
        try:
            si_bytes = inbox.read_bytes(si_file)
            bl_bytes = inbox.read_bytes(bl_file)
            extracted_pair = extract_pair_with_vision_gemini(si_bytes, bl_bytes)
        except Exception as e:
            print(f"[{email_id}] Vision extraction failed: {e}")
            return compare_documents({
                "SI": {"Error": "OCR Scan Failed - Unreadable characters %^&*"},
                "BL": {"Error": "OCR Scan Failed - Unreadable characters %^&*"}
            })

    # Convert Jayvan's Pydantic schemas to the dictionary format Barry expects
    jayvan_extracted_data = {
        "SI": extracted_pair.si_data.model_dump(),
        "BL": extracted_pair.bl_data.model_dump()
    }

    # -------------------------------------------------------------
    # STAGE 3: Semantic Verification & Diffing (Barry)
    # -------------------------------------------------------------
    result = compare_documents(jayvan_extracted_data)
    
    # Force category tag to remain compliant with the hackathon schema
    result["category"] = "BL_COMPARISON"
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("🚢 Testing Extractor -> Comparator Pipeline Integration")
    print("=" * 60)

    inbox = Inbox("http://localhost:8080")
    emails = inbox.emails()
    print(f"Loaded {len(emails)} emails from inbox.\n")

    # Run on first 5 emails as an integration test
    test_batch = emails[:5]
    for email in test_batch:
        eid = email.get("email_id")
        print(f"\n▶️ Processing {eid} | Subject: {email.get('subject', '')[:45]}...")
        
        output = process_email(inbox, email)
        
        print("Final Evaluation Payload:")
        print(json.dumps(output, indent=2))
        print("-" * 50)