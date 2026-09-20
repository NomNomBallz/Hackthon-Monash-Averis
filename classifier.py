import json
import os
import glob
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

class FinalClassifierPipeline:
    def __init__(self, api_key, inbox_dir="data_v2/inbox"):
        self.inbox_dir = inbox_dir
        self.batch_size = 15 
        self.categories = [
            "BL_COMPARISON", 
            "SI_REQUEST", 
            "INVOICE_QUERY", 
            "GENERAL", 
            "SPAM"
        ]
        
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-3.5-flash" 
        
        self.system_prompt = """
        You are an intelligent email classification routing system. 
        Analyze each email in the provided JSON list and classify it into exactly ONE of the following categories:
        BL_COMPARISON, SI_REQUEST, INVOICE_QUERY, GENERAL, SPAM.
        Return ONLY a valid JSON dictionary mapping 'email_id' to the category string.
        """

    def local_pre_filter(self, email_data):
        """
        Level 1: Local Python Filter. 
        Checks for spam, then checks for attachments, then checks subject keywords.
        """
        subject = email_data.get('subject', '').upper()
        full_text = f"{subject} {email_data.get('body', '').upper()}"

        # 1. SECURITY SHIELD (Highest Priority)
        suspicious_words = ["PRIZE", "PARCEL", "PHISHING", "WINNER", "CLICK HERE", "LOGIN", "URGENT", "ACCOUNT SUSPENDED"]
        if any(word in full_text for word in suspicious_words):
            return None # Send to AI immediately

        # 2. THE ATTACHMENT SHORTCUT
        # If there are 1 or more attachments, assume it requires BL/SI Comparison
        attachments = email_data.get('attachments', [])
        if len(attachments) > 0:
            return "BL_COMPARISON"

        # 3. FULL KEYWORD MATCHER (Subject Only)
        if any(phrase in subject for phrase in ["CUST SI", "REQUEST SI", "SI NEEDED", "SI -"]):
            return "SI_REQUEST"
            
        if any(phrase in subject for phrase in ["TO CONFIRM DOCS", "REQUEST BL DRAFT", "DRAFT BL", "AIE - ", "AFEMY - "]):
            return "BL_COMPARISON"
            
        if any(phrase in subject for phrase in ["BILLING", "MISSING GR", "CANCEL INVOICE", "TOTAL FREIGHT"]):
            return "INVOICE_QUERY"
            
        if any(phrase in subject for phrase in ["UPDATE SUMMARY", "BERTHING REPORT", "SLA", "_RPA_"]):
            return "GENERAL"

        # 4. FALLBACK: No attachments and no obvious keywords? Go to Gemini.
        return None

    def _call_ai_api_batch(self, batch_payload):
        user_prompt = json.dumps(batch_payload, indent=2)
        full_prompt = self.system_prompt + "\n\n" + user_prompt
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                    )
                )
                return json.loads(response.text)
                
            except Exception as e:
                error_message = str(e)
                if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message or "503" in error_message or "UNAVAILABLE" in error_message:
                    print(f"   [Server/Quota] Pausing for 10 seconds (Attempt {attempt + 1}/{max_retries})...")
                    time.sleep(10)
                    continue 
                return {} 
        return {} 

    def process_inbox(self):
        classified_emails = {category: [] for category in self.categories}
        ai_queue = [] 
        
        search_path = os.path.join(self.inbox_dir, "email_*.json")
        email_files = sorted(glob.glob(search_path)) 
        
        if not email_files:
            print(f"No emails found in {self.inbox_dir}")
            return classified_emails

        print(f"Starting Smart Classification for {len(email_files)} emails...\n")
        
        # --- PHASE 1: Python Speed Filter ---
        for file_path in email_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                email_data = json.load(f)
                
            local_category = self.local_pre_filter(email_data)
            
            if local_category:
                email_data['category'] = local_category
                classified_emails[local_category].append(email_data)
            else:
                ai_queue.append(email_data)
                
        print(f"⚡ Python instantly verified and categorized {len(email_files) - len(ai_queue)} emails.")
        print(f"🧠 Sending {len(ai_queue)} complex emails to Gemini API...\n")

        # --- PHASE 2: AI Batch Processing ---
        total_ai_files = len(ai_queue)
        for i in range(0, total_ai_files, self.batch_size):
            batch_data = ai_queue[i : i + self.batch_size]
            batch_payload = []
            
            for data in batch_data:
                batch_payload.append({
                    "email_id": data.get("email_id"),
                    "subject": data.get("subject"),
                    "body": data.get("body", "")[:400] 
                })

            print(f"Processing AI batch {i//self.batch_size + 1} of {(total_ai_files + self.batch_size - 1)//self.batch_size}...")
            batch_results = self._call_ai_api_batch(batch_payload)
            
            for data in batch_data:
                email_id = data.get("email_id")
                predicted_category = batch_results.get(email_id, "GENERAL")
                if predicted_category not in self.categories:
                    predicted_category = "GENERAL"
                    
                data['category'] = predicted_category
                classified_emails[predicted_category].append(data)
            
            if i + self.batch_size < total_ai_files:
                time.sleep(4.0)

        return classified_emails

    def export_for_member_3(self, classified_emails, output_file="filtered_bl_comparison.json"):
        bl_emails = classified_emails.get("BL_COMPARISON", [])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(bl_emails, f, indent=4)
        
        print(f"\n==================================================")
        print(f"✅ Handoff Ready! Exported {len(bl_emails)} BL_COMPARISON emails to {output_file}")
        print(f"==================================================")

if __name__ == "__main__":
    load_dotenv() 
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found in .env file.")
    else:
        classifier = FinalClassifierPipeline(api_key=GEMINI_API_KEY)
        results = classifier.process_inbox()
        classifier.export_for_member_3(results)