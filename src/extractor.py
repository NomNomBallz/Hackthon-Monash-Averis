# MEMBER 3's Code (Jayvan)
# Ingests raw document attachments (.txt, .pdf, .docx) and transforms them into structured ShippingDetails records. (check schemas.py for reference)
# Input: File bytes or raw text retrieved via inbox.read_bytes() / inbox.read_text().
# Output: Populated ShippingDetails object containing the 7 target fields.
# AI Suggested Strategy: Plain-text regex parser for standard .txt files; PyMuPDF/python-docx for clean digital files; 
# Gemini multimodal vision fallback for scanned or warped PDFs.