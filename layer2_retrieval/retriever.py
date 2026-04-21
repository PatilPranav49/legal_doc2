"""takes every IPC section and converts the text into a mathematical vector (embedding) using Legal-BERT.
It stores these vectors in a FAISS (Facebook AI Similarity Search) index. FAISS allows the app to find relevant 
laws in milliseconds, even if the user doesn't use the exact legal keywords."""

from typing import Dict, Any, Tuple, List
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

try:
    import faiss
    _has_faiss = True
except Exception:
    faiss = None
    _has_faiss = False


def build_index(df: pd.DataFrame, model_name: str = "nlpaueb/legal-bert-base-uncased", use_faiss: bool = True):

    model = SentenceTransformer(model_name)

    texts = []
    for _, r in df.iterrows():
        t = r.get("Formal_Legal_Text") or r.get("Description") or r.get("Offense") or ""
        texts.append(str(t))

    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    index_obj = None
    if use_faiss and _has_faiss:
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)  
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        index_obj = index
    else:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        embeddings = embeddings / norms

    return {
        "model": model,
        "embeddings": embeddings,
        "index": index_obj,
        "df": df.reset_index(drop=True),
    }


def search_scenario(scenario_text: str, index_data: Dict[str, Any], top_k: int = 3) -> List[Dict[str, Any]]:

    model: SentenceTransformer = index_data["model"]
    embeddings: np.ndarray = index_data["embeddings"]
    index = index_data["index"]
    df = index_data["df"]

    q_emb = model.encode([scenario_text], convert_to_numpy=True)

    results = []
    if index is not None:
        import faiss
        faiss.normalize_L2(q_emb)
        scores, ids = index.search(q_emb, top_k)
        scores = scores[0]
        ids = ids[0]
        for s, i in zip(scores, ids):
            if i < 0:
                continue
            row = df.iloc[i].to_dict()
            results.append({"score": float(s), "idx": int(i), **row})
    else:
        q_norm = q_emb / (np.linalg.norm(q_emb, axis=1, keepdims=True) + 1e-12)
        sims = (embeddings @ q_norm.T).squeeze()
        top_idx = np.argsort(-sims)[:top_k]
        for i in top_idx:
            row = df.iloc[i].to_dict()
            results.append({"score": float(sims[i]), "idx": int(i), **row})

    THRESHOLD = 0.55

    # 🔥 ADD THIS BLOCK HERE (before filtering loop)
    clause_text = scenario_text.lower()
    if any(k in clause_text for k in ["agreement", "tenant", "rent", "contract", "dispute"]):
        return []

    filtered = []

    for r in results:
        if r["score"] < THRESHOLD:
            continue

        desc = r.get("Formal_Legal_Text", "")

        # 🔥 apply domain filter
        if is_irrelevant_ipc(desc):
            continue

        filtered.append(r)

    return filtered
def is_irrelevant_ipc(text):
    text = str(text).lower()

    irrelevant_keywords = {
        "murder", "robbery", "theft", "dacoity",
        "assault", "weapon", "violence", "kidnap",

        "election", "public servant", "atmosphere",
        "nuisance", "forgery", "printer", "accounts",

        "repealed", "breach of contract (repealing)"
    }

    return any(k in text for k in irrelevant_keywords)

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="Cleaned IPC CSV path (with Offense column)")
    parser.add_argument("--no-faiss", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(Path(args.csv))
    print("Building index (this may take a minute)...")
    index_data = build_index(df, use_faiss=not args.no_faiss)
    print("Index built. Example search:")
    res = search_scenario("I was threatened for money", index_data, top_k=3)
    for r in res:
        print(r.get("Section"), r.get("Offense"), r.get("score"))
