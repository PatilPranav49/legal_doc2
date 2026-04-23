import re

class ClauseSplitter:

    @staticmethod
    def split(text: str):
        if not text or not text.strip():
            return []

        # Normalize spacing
        text = re.sub(r'\s+', ' ', text).strip()

        # Primary split (sentence based)
        clauses = re.split(r'(?<=[।.!?])\s+', text)

        clauses = [c.strip() for c in clauses if len(c.strip()) > 30]

        # ✅ Controlled fallback (only if nothing found)
        if not clauses:
            return [text[:500]]

        return clauses