# MEMBER 4's Code (Barry)
# Compares the extracted SI fields against the draft BL fields, applies domain-specific normalization, detects defects, and routes unresolvable cases.
# Input: si_data: ShippingDetails, bl_data: ShippingDetails, and attachment status.
# Output: Discrepancy status ('OK', 'MISMATCH', or 'NEEDS_REVIEW'), defective field names list, and review reason ('missing_attachment', 'unreadable', 'wrong_doc_type', 'missing_value').
# AI Suggested Strategy: Token fuzzy matching (rapidfuzz) for entity names and ports; numeric tolerances and unit conversion (lbs to kg) for weights; container 
# count integer matching. 

import json
import os
import time
from typing import Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load variables from .env
load_dotenv()
my_api_key = os.getenv("GCP_API_KEY")
client = genai.Client(api_key=my_api_key)

#checks the required 7 key fields
REQUIRED_KEYS = [
    "shipper", "consignee", "notify_party", 
    "port_of_loading", "port_of_discharge", 
    "container_count", "gross_weight_kg"
]
PLACEHOLDERS = {"TBA", "???", "_______", "NONE", ""}

def is_empty_or_placeholder(val: Any) -> bool:
    """Helper to detect true nulls or placeholder strings from OCR."""
    if val is None:
        return True
    return str(val).strip().upper() in PLACEHOLDERS

def compare_documents(jayvan_extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """ (official instruction manual for this function)
    Compares 7 key logistics fields between a Shipping Instruction (SI) and Bill of Lading (BL).
    Uses a hybrid approach: 0ms Python structural checks for missing/corrupted data, 
    falling back to an LLM strictly for semantic text comparison.
    
    Args (what it needs):
        jayvan_extracted_data (dict): A dictionary containing 'SI' and 'BL' nested dictionaries.
        
    Returns (what it spits ou/return):
        dict: A strict 5-field grading dictionary required for the hackathon 
    """
    # ==========================================
    #Python fast path checks
    # ==========================================
    # Failsafe payload for routing to Human in the-Loop review
    fallback_payload = {
        "category": "BL_COMPARISON", 
        "status": "NEEDS_REVIEW", 
        "has_defect": False, 
        "defect_fields": []
    }

    if not isinstance(jayvan_extracted_data, dict) or not jayvan_extracted_data:
        return {**fallback_payload, "review_reason": "unreadable"}

    si = jayvan_extracted_data.get("SI")
    bl = jayvan_extracted_data.get("BL")

    # Rule 1: missing_attachment
    if not isinstance(si, dict) or not isinstance(bl, dict):
        return {**fallback_payload, "review_reason": "missing_attachment"}

    # Rule 1: unreadable (OCR failure)
    si_str, bl_str = str(si), str(bl)
    if "OCR Scan Failed" in si_str or "OCR Scan Failed" in bl_str or "%^&*" in si_str:
        return {**fallback_payload, "review_reason": "unreadable"}

    # Rule 1: wrong_doc_type
    doc_titles = str(si.get("Document_Title", "")).upper() + " " + str(bl.get("Document_Title", "")).upper()
    if any(wrong in doc_titles for wrong in ["COMMERCIAL INVOICE", "PACKING LIST", "CERTIFICATE OF ORIGIN"]):
        return {**fallback_payload, "review_reason": "wrong_doc_type"}

    # Rule 1: missing_value check across the 7 contract keys
    for k in REQUIRED_KEYS:
        if k not in si or is_empty_or_placeholder(si[k]) or k not in bl or is_empty_or_placeholder(bl[k]):
            return {**fallback_payload, "review_reason": "missing_value"}

  #ai prompt
    system_instruction = """
    You are an expert shipping logistics comparator. I will provide you with extracted JSON data representing 7 key fields from a Shipping Instruction (SI) and a Bill of Lading (BL).
    
    The 7 strict keys you must evaluate are: shipper, consignee, notify_party, port_of_loading, port_of_discharge, container_count, gross_weight_kg.
    
    Your task is to compare these 7 fields logically. Note that the text might have slight formatting differences, but you must evaluate if the *meaning and values* are truly identical or different.
    
    LOGICAL MATCHING RULES (Ignore Formatting):
    * Ignore uppercase/lowercase (e.g., "GLOBAL TECH" == "Global Tech").
    * Ignore punctuation and symbols (e.g., "ABC, LLC." == "ABC LLC").
    * Ignore word order if the meaning is identical (e.g., "Klang Port" == "Port Klang").
    * Ignore semantic phrasing if the core entity is identical (e.g., "Receiver of Cargo: ABC Corp" == "ABC Corp", "Same as Consignee" == the actual consignee name).
    * Ignore unit formatting and data types if the mathematical value is identical (e.g., for gross_weight_kg: "2000", 2000, and 2000.0 are all identical matches).
    
    RULE 2: MISMATCH (Defects Found)
    If the documents are valid, compare the fields using the Logical Matching Rules. If one or more fields logically differ (e.g., container_count is 5 vs 6, or port_of_discharge is "Los Angeles" vs "Long Beach"), set "status": "MISMATCH", "has_defect": true, "review_reason": null, and list the EXACT JSON keys (e.g., ["gross_weight_kg", "port_of_discharge"]) of the broken fields inside the "defect_fields" array.
    
    RULE 3: OK (Perfect Match)
    If all 7 fields logically match between the SI and BL, set "status": "OK", "has_defect": false, "defect_fields": [], and "review_reason": null.
    
    OUTPUT FORMAT:
    You must return ONLY a raw JSON object using the exact "Wrapper" structure below. Do not wrap it in markdown code blocks. 
    Use the "debug_log" field to explain your thought process. Place the strict grading output inside "final_hackathon_output".
    
    {
      "debug_log": "Write your internal reasoning here.",
      "final_hackathon_output": {
        "category": "BL_COMPARISON",
        "status": "OK",
        "review_reason": null,
        "has_defect": false,
        "defect_fields": []
      }
    }
    """

    user_prompt = f"Data to compare: {json.dumps(jayvan_extracted_data)}"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            chat = client.chats.create(
                #ai's model
                model='gemini-3.6-flash',
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.0,
                )
            )
            response = chat.send_message(user_prompt)
            ai_wrapper = json.loads(response.text)
            
            print("🤖 AI DEBUG LOG:", ai_wrapper.get("debug_log", ""))
            return ai_wrapper.get("final_hackathon_output")
            
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} error detail: {e}")
            if "503" in str(e) or "429" in str(e):
                time.sleep(2 * (attempt + 1))
                continue
            break

    print("❌ LLM path failed, returning fallback.")
    return {**fallback_payload, "review_reason": "unreadable"}


# Local tesing ground(Ignored by pipeline.py)
if __name__ == "__main__":
    print("\n🚀 RUNNING HYBRID COMPARATOR TEST SUITE...\n")

    test_cases = [
        {
            "name": "TEST 1: Perfect Semantic Match (The 'OK' Status)",
            "data": {
                "SI": {"shipper": "Global Tech LLC", "consignee": "Receiver of Cargo: ABC Corp", "notify_party": "Same as Consignee", "port_of_loading": "Shanghai Port", "port_of_discharge": "Los Angeles", "gross_weight_kg": "2000 kg", "container_count": 5},
                "BL": {"shipper": "GLOBAL TECH, LLC.", "consignee": "ABC Corp", "notify_party": "ABC Corp", "port_of_loading": "Shanghai", "port_of_discharge": "Los Angeles", "gross_weight_kg": "2,000 Kilograms", "container_count": 5}
            }
        },
        {
            "name": "TEST 2: Factual Mismatch (The 'MISMATCH' Status)",
            "data": {
                "SI": {"shipper": "Global Tech", "consignee": "ABC", "notify_party": "XYZ", "port_of_loading": "SH", "port_of_discharge": "Los Angeles", "gross_weight_kg": 2000, "container_count": 5},
                "BL": {"shipper": "Global Tech", "consignee": "ABC", "notify_party": "XYZ", "port_of_loading": "SH", "port_of_discharge": "Long Beach", "gross_weight_kg": 3000, "container_count": 5}
            }
        },
        {
            "name": "TEST 3: Missing Document (Rule 1: missing_attachment)",
            "data": {"SI": {"shipper": "Global Tech"}, "BL": None}
        },
        {
            "name": "TEST 4: Missing/Placeholder Value (Rule 1: missing_value)",
            "data": {
                "SI": {"shipper": "Global Tech", "consignee": "ABC", "notify_party": "XYZ", "port_of_loading": "SH", "port_of_discharge": "LA", "gross_weight_kg": 2000, "container_count": 5},
                "BL": {"shipper": "Global Tech", "consignee": "ABC", "notify_party": "XYZ", "port_of_loading": "SH", "port_of_discharge": "LA", "gross_weight_kg": "TBA", "container_count": 5}
            }
        },
        {
            "name": "TEST 5: Wrong Document Type (Rule 1: wrong_doc_type)",
            "data": {
                "SI": {"Document_Title": "COMMERCIAL INVOICE", "shipper": "A", "consignee": "B", "notify_party": "C", "port_of_loading": "D", "port_of_discharge": "E", "gross_weight_kg": 1, "container_count": 1},
                "BL": {"shipper": "A", "consignee": "B", "notify_party": "C", "port_of_loading": "D", "port_of_discharge": "E", "gross_weight_kg": 1, "container_count": 1}
            }
        },
        {
            "name": "TEST 6: Unreadable/Corrupted Data (Rule 1: unreadable)",
            "data": {
                "SI": {"Error": "OCR Scan Failed - Unreadable characters %^&*"},
                "BL": {"shipper": "Global Tech"}
            }
        },
        {
            "name": "TEST 7: Edge Case - True Nulls vs String Nones (Python Fast-Path)",
            "data": {
                "SI": {"shipper": "Tech", "consignee": None, "notify_party": "XYZ", "port_of_loading": "SH", "port_of_discharge": "LA", "gross_weight_kg": 2000, "container_count": 5},
                "BL": {"shipper": "Tech", "consignee": "None", "notify_party": "XYZ", "port_of_loading": "SH", "port_of_discharge": "LA", "gross_weight_kg": 2000, "container_count": 5}
            }
        },
        {
            "name": "TEST 8: Edge Case - Keys Completely Missing (Python Fast-Path)",
            "data": {
                "SI": {"shipper": "Global Tech", "consignee": "ABC Corp", "notify_party": "XYZ", "port_of_loading": "SH", "port_of_discharge": "LA"}, 
                "BL": {"shipper": "Global Tech", "consignee": "ABC Corp", "notify_party": "XYZ", "port_of_loading": "SH", "port_of_discharge": "LA"}
            }
        },
        {
            "name": "TEST 9: Edge Case - Totally Empty / Malformed Payload (Python Fast-Path)",
            "data": {} 
        }
    ]

    for test in test_cases:
        print(f"\n{'='*60}\n▶️ {test['name']}\n{'='*60}")
        out = compare_documents(test['data'])
        print(json.dumps(out, indent=2))
        time.sleep(1)
