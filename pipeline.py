# MEMBER 1's Code (Cham)
# Handles load, execute and submit operations
# Generates submission.json

import os
import pymupdf as fitz
from google import genai
from pydantic import BaseModel, Field
from typing import Optional
from loader import Inbox
from dotenv import load_dotenv

# Define the exact 7 fields
class ShippingDocument(BaseModel):
    shipper: Optional[str] = Field(None, description="Shipper entity name")
    consignee: Optional[str] = Field(None, description="Consignee entity name")
    notify_party: Optional[str] = Field(None, description="Notify party")
    port_of_loading: Optional[str] = Field(None, description="Port of loading / departure / POL")
    port_of_discharge: Optional[str] = Field(None, description="Port of discharge / destination / POD")
    container_count: Optional[int] = Field(None, description="Total container count as an integer")
    gross_weight_kg: Optional[float] = Field(None, description="Gross weight strictly normalized to KG")

# Initialize structured extraction client
# Initialize native Gemini client
load_dotenv()
client = genai.Client(api_key=os.getenv("GCP_API_KEY"))

def extract_shipping_data(doc_text: str, doc_type: str = "SI") -> ShippingDocument:
    """Extracts structured shipment fields natively using Gemini."""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Extract the 7 key shipment fields from this {doc_type}:\n\n{doc_text}",
        config={
            "response_mime_type": "application/json",
            "response_schema": ShippingDocument,
        },
    )
    return ShippingDocument.model_validate_json(response.text)

def extract_document_text(file_path: str) -> str:
    """Handles .txt, .docx, and digital .pdf cleanly."""
    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    if file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    if file_path.endswith(".pdf"):
        doc = fitz.open(file_path)
        return "\n".join([page.get_text() for page in doc])
    return ""

def extract_shipping_data(doc_text: str, doc_type: str = "SI") -> ShippingDocument:
    """Extracts structured shipment fields from raw text."""
    return client.chat.completions.create(
        model="gemini-2.5-flash",
        response_model=ShippingDocument,
        messages=[
            {
                "role": "system",
                "content": f"You are a shipping documentation auditor. Extract the 7 key shipment fields from this {doc_type}."
            },
            {"role": "user", "content": doc_text},
        ],
    )

if __name__ == "__main__":
    print("Connecting to inbox...")
    # Change "data" to "http://localhost:8080" if your Docker container is up
    inbox = Inbox("http://localhost:8080")
    
    emails = inbox.emails()
    print(f"Loaded {len(emails)} emails from inbox.")

    # Grab the first email
    first_email = emails[0]
    print(f"\nProcessing first email: {first_email['email_id']}")
    print(f"Subject: {first_email.get('subject')}")
    print(f"Attachments: {first_email.get('attachments')}")

    # Test attachment reading and extraction if attachments exist
    attachments = first_email.get("attachments", [])
    if attachments:
        first_att = attachments[0]
        print(f"\nReading attachment: {first_att}")
        text = inbox.read_text(first_att)
        print("Attachment snippet:", text[:120].replace("\n", " "))

        print("\nTesting Gemini extraction on this attachment...")
        extracted = extract_shipping_data(text, doc_type="SI")
        print("Extracted fields successfully:")
        print(extracted.model_dump_json(indent=2))
    else:
        print("No attachments on the first email.")