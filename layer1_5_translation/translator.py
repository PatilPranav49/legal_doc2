import requests
import re
import os
from config import Config


LANGDETECT_TO_SARVAM = {
    "hi": "hi-IN",
    "mr": "mr-IN",
    "en": "en-IN",
    "bn": "bn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
}


def detect_script(text: str) -> str:
    sample = text[:500]

    devanagari = sum(1 for c in sample if '\u0900' <= c <= '\u097F')
    english = sum(1 for c in sample if c.isascii() and c.isalpha())
    total = max(len(sample), 1)

    if devanagari / total > 0.3:
        marathi_chars = sum(1 for c in sample if c in 'ळञऑ')
        marathi_words = len(re.findall(
            r'आहे|करणे|येते|यावा|राहिल|असून|होईल|मुळे|सर्व|यांचे|देण्यात|घेणे',
            sample
        ))
        hindi_words = len(re.findall(
            r'है|हैं|करना|होना|यहाँ|वहाँ|लेकिन|इसलिए|जैसे|उनका|करें|होगा',
            sample
        ))

        if marathi_words >= hindi_words or marathi_chars > 0:
            return "mr-IN"
        return "hi-IN"

    if english / total > 0.7:
        return "en-IN"

    return "hi-IN"


def chunk_text(text: str, max_chars: int = 900) -> list:
    chunks = []
    sentences = re.split(r'(?<=[।.!\n])\s*', text)

    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) <= max_chars:
            current += sentence + " "
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sentence + " "

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text]


class LanguageTranslator:

    def detect_language(self, text: str) -> dict:
        sarvam_code = detect_script(text)
        short_code = sarvam_code.split("-")[0]
        return {
            "lang_code": short_code,
            "confidence": 1.0
        }

    # 🔥 ONLY THIS FUNCTION CHANGED (Sarvam → Gemini)
    def _translate_chunk(self, chunk: str, source_lang: str, api_key: str) -> str:

        import os

        gemini_key = (
            os.environ.get("GEMINI_API_KEY_1") or
            os.environ.get("GEMINI_API_KEY_2")
        )

        if not gemini_key:
            return chunk

        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={gemini_key}"

        prompt = f"""
Translate the following text into clear English.

Rules:
- Preserve meaning exactly
- Fix OCR mistakes if possible
- Do NOT explain anything
- Return ONLY translated text

Text:
{chunk}
"""

        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ]
        }

        try:
            response = requests.post(url, json=body, timeout=10)

            if response.status_code == 200:
                data = response.json()

                candidates = data.get("candidates", [])
                if not candidates:
                    return chunk

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    return chunk

                translated = parts[0].get("text", "").strip()

                if translated:
                    return translated

            elif response.status_code == 429:
                print("Translation quota hit → returning original")

        except Exception as e:
            print("Gemini translation error:", e)

        return chunk

    def translate_to_english(self, text: str) -> str:
        if not text or len(text.strip()) < 10:
            return text

        source_lang = detect_script(text)

        if source_lang == "en-IN":
            return text

        if not (Config.SARVAM_API_KEYS or 
                os.environ.get("GEMINI_API_KEY_1") or 
                os.environ.get("GEMINI_API_KEY")):
            return text

        api_key = Config.SARVAM_API_KEYS[0]

        chunks = chunk_text(text, max_chars=900)

        translated_parts = []
        for chunk in chunks:
            result = self._translate_chunk(chunk, source_lang, api_key)
            translated_parts.append(result)

        return "\n".join(translated_parts)