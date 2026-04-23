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
You are helping a normal Indian citizen understand a legal clause.

Explain the meaning in simple, practical English.

STRICT RULES:
- Do NOT repeat the clause
- Do NOT rewrite the same sentence
- Do NOT give multiple options
- Do NOT include Hindi
- Keep it short (1–2 lines)
- Focus on what the user should understand or do

Then classify:

Type: ONE WORD from [Obligation, Penalty, Liability, Termination, General]
Risk: ONE WORD from [Low, Medium, High]

Clause:
{english}

Context:
{context}

Output format EXACTLY:

Explanation: <your explanation>
Type: <value>
Risk: <value>
"""

    def _call_llm(self, prompt):
        self._throttle()   # ✅ ensure spacing between calls

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

            try:
                response = requests.post(url, json=body, timeout=20)

                print(f"Key {key_index+1} | STATUS:", response.status_code)

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
                    print(f"Key {key_index+1} rate-limited → switching key")
                    continue  # try next key immediately

                else:
                    print(f"Key {key_index+1} failed with status:", response.status_code)
                    continue

            except Exception as e:
                print(f"Key {key_index+1} error:", e)
                continue

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
    
    def analyze_clauses_batch(self, clauses):
        if not clauses:
            return []

        numbered = "\n".join([f"{i+1}. {c}" for i, c in enumerate(clauses)])

        prompt = f"""
    You are explaining legal clauses to a normal Indian citizen.

    Explain each clause in simple English.

    STRICT RULES:
    - Do NOT repeat the clause
    - Do NOT paraphrase
    - Do NOT give multiple options
    - Do NOT include Hindi
    - Keep each explanation short (1 line)

    Clauses:
    {numbered}

    Return EXACTLY in this format:

    1. <explanation>
    2. <explanation>
    3. <explanation>
    """

        response = self._call_llm(prompt)

        if not response:
            return ["No explanation available"] * len(clauses)

        lines = response.split("\n")
        explanations = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # remove numbering
            if "." in line:
                line = line.split(".", 1)[1].strip()

            explanations.append(line)

        # fallback safety
        while len(explanations) < len(clauses):
            explanations.append("General information provided.")

        return explanations[:len(clauses)]
    def explain_clauses_batch(self, clauses):
        if not clauses:
            return []

        numbered = "\n".join([f"{i+1}. {c}" for i, c in enumerate(clauses)])

        prompt = f"""
    Explain the meaning of each clause in simple English.

    STRICT RULES:
    - Do NOT repeat the clause
    - Do NOT give options
    - Do NOT include Hindi
    - Keep each explanation short (1 line)

    Clauses:
    {numbered}

    Return EXACTLY like:

    1. <explanation>
    2. <explanation>
    3. <explanation>
    """

        response = self._call_llm(prompt)

        if not response:
            return ["General information"] * len(clauses)

        lines = response.split("\n")
        results = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "." in line:
                line = line.split(".", 1)[1].strip()

            results.append(line)

        # safety padding
        while len(results) < len(clauses):
            results.append("General information")

        return results[:len(clauses)]