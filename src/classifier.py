# MEMBER 2's code (ryan)
# classify email categories 
# Input: Raw email dictionary (subject, body, attachments).
# Output: One exact category string: 'BL_COMPARISON', 'SI_REQUEST', 'INVOICE_QUERY', 'GENERAL', or 'SPAM'.
# AI Suggested Strategy: Fast pattern-matching heuristics or a structured Gemini 2.5 Flash classification prompt.


import json
import os
import time
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class EmailClassifier:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.categories = [
            "BL_COMPARISON", 
            "SI_REQUEST", 
            "INVOICE_QUERY", 
            "GENERAL", 
            "SPAM"
        ]
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.model_name = "gemini-2.5-flash"
        
        self.system_prompt = """
        You are an intelligent email classification routing system for maritime freight.
        Analyze the email subject and body and classify it into exactly ONE of the following categories:
        BL_COMPARISON, SI_REQUEST, INVOICE_QUERY, GENERAL, SPAM.
        
        Return JSON with a single key 'category'.
        """

    def fast_heuristic_filter(self, email_data: Dict[str, Any]) -> Optional[str]:
        """Speed filter: checks high-confidence keywords without misrouting attachments."""
        subject = email_data.get("subject", "").upper()
        full_text = f"{subject} {email_data.get('body', '').upper()}"

        # 1. Security / Spam Check
        suspicious_words = ["PRIZE", "PARCEL", "PHISHING", "WINNER", "CLICK HERE", "LOGIN", "ACCOUNT SUSPENDED"]
        if any(word in full_text for word in suspicious_words):
            return "SPAM"

        # 2. Subject Exact Keywords
        if any(phrase in subject for phrase in ["CUST SI", "REQUEST SI", "SI NEEDED", "SI -"]):
            return "SI_REQUEST"
            
        if any(phrase in subject for phrase in ["TO CONFIRM DOCS", "REQUEST BL DRAFT", "DRAFT BL", "AIE - ", "AFEMY - "]):
            return "BL_COMPARISON"
            
        if any(phrase in subject for phrase in ["BILLING", "MISSING GR", "CANCEL INVOICE", "TOTAL FREIGHT"]):
            return "INVOICE_QUERY"
            
        if any(phrase in subject for phrase in ["UPDATE SUMMARY", "BERTHING REPORT", "SLA", "_RPA_"]):
            return "GENERAL"

        # Fallback to AI
        return None

    def classify_single(self, email_data: Dict[str, Any]) -> str:
        """Classify a single email: heuristic first, then Gemini."""
        quick_cat = self.fast_heuristic_filter(email_data)
        if quick_cat:
            return quick_cat

        if not self.client:
            return "GENERAL"

        prompt = f"Subject: {email_data.get('subject', '')}\nBody: {email_data.get('body', '')[:1000]}"

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            parsed = json.loads(response.text)
            cat = parsed.get("category", "GENERAL")
            return cat if cat in self.categories else "GENERAL"
        except Exception as e:
            print(f"Classification API fallback error: {e}")
            return "GENERAL"