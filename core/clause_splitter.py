import re


class ClauseSplitter:

    @staticmethod
    def split(text: str):
        if not text or not text.strip():
            return []

        # Normalize spacing
        text = re.sub(r'\s+', ' ', text).strip()

        # 🔥 Better splitting
        clauses = re.split(r'(?<=[।.!?])\s+', text)


        return [c.strip() for c in clauses if len(c.strip()) > 30]