import os
import requests
import time
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(dotenv_path=ENV_PATH)


def fallback_explanation(clause):
    return {
        "explanation": f"This clause describes: {clause[:100]}...",
        "risk": "Low",
        "type": "General"
    }


class LegalLLMAdapter:

    def __init__(self):
        self.keys = [
            os.environ.get("GEMINI_API_KEY_1"),
            os.environ.get("GEMINI_API_KEY_2")
        ]
        self.last_call_time = 0

    def __init__(self):
        self.keys = [
            os.environ.get("GEMINI_API_KEY_1"),
            os.environ.get("GEMINI_API_KEY_2")
        ]
        self.last_call_time = 0

    def _throttle(self, min_interval=2.0):
        now = time.time()
        elapsed = now - self.last_call_time

        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

        self.last_call_time = time.time()

    def explain_clause(self, original, english, context):
        prompt = self._build_prompt(original, english, context)

        response = None

        try:
            response = self._call_llm(prompt)
        except Exception as e:
            print("Gemini failed:", str(e))

        if not response or not isinstance(response, str):
            return fallback_explanation(english)

        return self._parse_response(response)

    def _build_prompt(self, original, english, context):
        return f"""
You are an Indian legal assistant.

Return output STRICTLY in EXACT format:

Explain this clause in simple, user-friendly language. Start with "This means..." and avoid repeating the sentence. <max 2 lines>

Type: <ONE WORD ONLY from [Obligation, Penalty, Liability, Termination, General]>

Risk: <ONE WORD ONLY from [Low, Medium, High]>

Clause:
{english}

Context:
{context}

RULES:
- Type MUST be exactly one of: Obligation / Penalty / Liability / Termination / General
- Risk MUST be exactly one of: Low / Medium / High
- Do NOT write anything else
"""

    def _call_llm(self, prompt):
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ]
        }

        for key_index, key in enumerate(self.keys):

            if not key:
                continue

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"

            # 🔥 2 attempts per key
            for attempt in range(2):
                try:
                    response = requests.post(url, json=body, timeout=20)

                    print(f"Key {key_index+1} | Attempt {attempt+1} | STATUS:", response.status_code)

                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])

                        if not candidates:
                            continue

                        parts = candidates[0].get("content", {}).get("parts", [])
                        if not parts:
                            continue

                        text = parts[0].get("text", "")
                        return text.strip() if text else None

                    elif response.status_code in [429, 503]:
                        print("Retrying same key...")
                        time.sleep(2)
                        continue

                    else:
                        break  # other errors → move to next key

                except Exception as e:
                    print("Error:", e)
                    time.sleep(2)

        return None
    def _parse_response(self, text):

        if not text or not isinstance(text, str):
            return fallback_explanation(text or "")

        explanation = ""
        risk = "Unknown"
        ctype = "General"

        lines = text.split("\n")

        for line in lines:
            l = line.lower()

            if "explanation" in l:
                explanation = line.split(":", 1)[-1].strip()

            elif "type" in l:
                value = line.split(":", 1)[-1].strip().lower()

                if "obligation" in value:
                    ctype = "Obligation"
                elif "penalty" in value:
                    ctype = "Penalty"
                elif "liability" in value:
                    ctype = "Liability"
                elif "termination" in value:
                    ctype = "Termination"

            elif "risk" in l:
                value = line.split(":", 1)[-1].strip().lower()

                if "low" in value:
                    risk = "Low"
                elif "medium" in value:
                    risk = "Medium"
                elif "high" in value:
                    risk = "High"

        if not explanation:
            explanation = text.strip() if text else "No explanation generated"

        return {
            "explanation": explanation,
            "risk": risk,
            "type": ctype
        }