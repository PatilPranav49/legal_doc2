import pandas as pd
from pathlib import Path
import  math
from .retriever import build_index, search_scenario


DATA_PATH = Path(__file__).parent / "ipc_data.csv"


class LegalRetrievalAdapter:
    def __init__(self):
        # Load IPC dataset
        self.df = pd.read_csv(DATA_PATH)

        # Build index ONCE (very important)
        self.index = build_index(self.df, use_faiss=True)


    def retrieve(self, text: str, top_k: int = 3):
        if not text or not text.strip():
            return []

        results = search_scenario(text, self.index, top_k=top_k)

        cleaned = []
        for r in results:
            # 🔹 Safe score handling
            score = r.get("score", 0.0)

            try:
                score = float(score)
                if not math.isfinite(score):   # handles NaN, inf
                    score = 0.0
            except Exception:
                score = 0.0

            cleaned.append({
                "section": str(r.get("Section", "")),
                "offense": str(r.get("Offense", "")),
                "punishment": str(r.get("Punishment", "")),
                "description": str(r.get("Formal_Legal_Text", "")),
                "score": score
            })

        return cleaned