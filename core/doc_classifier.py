def classify_document(text):

    t = text.lower()

    # 🔴 HIGH-IMPORTANCE LEGAL DOCS

    if any(x in t for x in ["rent agreement", "lease agreement", "tenant", "landlord"]):
        return "Rent Agreement"

    if any(x in t for x in ["agreement", "party", "terms and conditions", "contract"]):
        return "Contract"

    if any(x in t for x in ["fir", "first information report", "police station", "complainant"]):
        return "FIR"

    if any(x in t for x in ["court", "summons", "hearing", "petition"]):
        return "Court Notice"
    
    if "notice" in t and "court" in t:
        return "Court Notice"

    if any(x in t for x in ["vs", "v.", "case no", "petitioner", "respondent"]):
        return "Case Document"

    # 🟢 LOW-RISK DOCS

    if any(x in t for x in ["government of india", "ministry", "department"]):
        return "Government Document"

    return "General Document"


def is_risk_relevant(doc_type):

    return doc_type in [
        "Contract",
        "Rent Agreement",
        "FIR",
        "Court Notice",
        "Case Document"
    ]