import os
import re
import time
import itertools
from typing import Optional, List, Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from groq import Groq, GroqError
from google import genai
from google.genai import types

load_dotenv()


class ShippingDocumentData(BaseModel):
    shipper: Optional[str] = Field(default=None)
    consignee: Optional[str] = Field(default=None)
    notify_party: Optional[str] = Field(default=None)
    port_of_loading: Optional[str] = Field(default=None)
    port_of_discharge: Optional[str] = Field(default=None)
    container_count: Optional[int] = Field(default=None)
    gross_weight_kg: Optional[float] = Field(default=None)

    @field_validator("container_count", mode="before")
    @classmethod
    def parse_container_count(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            match = re.search(r"\b(\d+)\b", v)
            if match:
                return int(match.group(1))
        return None

    @field_validator("gross_weight_kg", mode="before")
    @classmethod
    def parse_gross_weight(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            cleaned = v.replace(",", "")
            match = re.search(r"([\d\.]+)", cleaned)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    return None
        return None


class DocumentPairExtraction(BaseModel):
    si_data: ShippingDocumentData
    bl_data: ShippingDocumentData


def _initialize_groq_clients() -> List[Groq]:
    keys = [
        os.getenv("GROQ_API_KEY_1"),
        os.getenv("GROQ_API_KEY_2"),
        os.getenv("GROQ_API_KEY_3"),
        os.getenv("GROQ_API_KEY"),
    ]
    valid_keys = [k for k in keys if k and k.strip()]

    if not valid_keys:
        raise ValueError("No valid GROQ_API_KEY found in environment variables (.env).")

    return [Groq(api_key=key) for key in valid_keys]


_CLIENTS = _initialize_groq_clients()
_CLIENT_CYCLE = itertools.cycle(_CLIENTS)


def get_next_groq_client() -> Groq:
    return next(_CLIENT_CYCLE)


def extract_pair_with_groq(si_text: str, bl_text: str, max_retries: int = 3) -> DocumentPairExtraction:
    """Standard text extraction using fast Groq key rotation."""
    prompt = f"""
    Extract the 7 canonical fields for BOTH Document 1 (SI) and Document 2 (BL).
    Fields: shipper, consignee, notify_party, port_of_loading, port_of_discharge, container_count, gross_weight_kg.

    --- DOCUMENT 1: SHIPPING INSTRUCTION (SI) ---
    {si_text[:3500]}

    --- DOCUMENT 2: DRAFT BILL OF LADING (BL) ---
    {bl_text[:3500]}
    """

    for attempt in range(1, max_retries + 1):
        client = get_next_groq_client()
        
        try:
            completion = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "You are a precise JSON extractor for shipping logistics documents."},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "document_pair_extraction",
                        "schema": DocumentPairExtraction.model_json_schema(),
                    }
                },
                temperature=0.0
            )
            raw_json = completion.choices[0].message.content
            return DocumentPairExtraction.model_validate_json(raw_json)

        except GroqError as e:
            if ("429" in str(e) or "rate_limit" in str(e).lower()) and attempt < max_retries:
                time.sleep(1.0)
            else:
                raise e


def extract_pair_with_vision_gemini(si_input: Union[str, bytes], bl_input: Union[str, bytes]) -> DocumentPairExtraction:
    """Multimodal Vision extraction using Gemini 2.5 Flash for scanned image PDFs."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY is not configured in environment variables.")

    client = genai.Client(api_key=gemini_key)

    prompt = (
        "Extract the 7 canonical fields (shipper, consignee, notify_party, port_of_loading, "
        "port_of_discharge, container_count, gross_weight_kg) for Document 1 (SI) and Document 2 (BL)."
    )

    contents = [prompt]

    # Process Document 1 (SI)
    if isinstance(si_input, bytes):
        contents.append("Document 1 (SI):")
        contents.append(types.Part.from_bytes(data=si_input, mime_type="image/jpeg"))
    else:
        contents.append(f"Document 1 (SI):\n{si_input[:2000]}")

    # Process Document 2 (BL)
    if isinstance(bl_input, bytes):
        contents.append("Document 2 (BL):")
        contents.append(types.Part.from_bytes(data=bl_input, mime_type="image/jpeg"))
    else:
        contents.append(f"Document 2 (BL):\n{bl_input[:2000]}")

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DocumentPairExtraction,
            temperature=0.0,
        ),
    )

    return DocumentPairExtraction.model_validate_json(response.text)