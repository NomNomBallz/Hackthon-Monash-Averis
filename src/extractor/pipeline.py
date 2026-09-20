from .doc_parser import parse_attachment
from .extractor import extract_pair_with_groq, extract_pair_with_vision_gemini

def extract_si_bl_pair(si_path: str, bl_path: str) -> dict:
    try:
        si_parsed = parse_attachment(si_path)
        bl_parsed = parse_attachment(bl_path)

        # Route to Gemini Vision API if either document requires image recognition
        if si_parsed["type"] == "image" or bl_parsed["type"] == "image":
            extracted_pair = extract_pair_with_vision_gemini(si_parsed["content"], bl_parsed["content"])
            source = "GEMINI_VISION_LLM"
        else:
            extracted_pair = extract_pair_with_groq(si_parsed["content"], bl_parsed["content"])
            source = "GROQ_LLM"

        return {
            "status": "SUCCESS",
            "si_data": extracted_pair.si_data.model_dump(),
            "bl_data": extracted_pair.bl_data.model_dump(),
            "source": source
        }

    except Exception as e:
        return {
            "status": "UNREADABLE_DOCUMENT",
            "si_data": None,
            "bl_data": None,
            "error": str(e)
        }