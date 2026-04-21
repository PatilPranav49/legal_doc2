from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from core.pipeline_adapter import extract_using_pipeline

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/process")
async def process_file(file: UploadFile = File(...)):
    contents = await file.read()
    filename = file.filename

    print("Received:", filename)

    try:
        result = extract_using_pipeline(contents, filename)

        original_text  = result.get("original_text", "")
        english_text   = result.get("english_text", "")
        pii_summary    = result.get("pii_summary", "")
        detected_lang  = result.get("detected_language", "unknown")
        legal_context  = result.get("legal_context", [])      # ✅ ADD THIS
        retrieval_count = result.get("retrieval_count", 0)    # ✅ ADD THIS

        print("Preview:\n", original_text[:200])
        print("English preview:\n", english_text[:200])
        print("Clauses analyzed:", retrieval_count)

    except Exception as e:
        original_text   = f"Error: {str(e)}"
        english_text    = ""
        pii_summary     = ""
        detected_lang   = "unknown"
        legal_context   = []
        retrieval_count = 0

    return {
        "document_type":      "Extracted Document",
        "summary":            original_text[:300],
        "full_text":          original_text,
        "english_text":       english_text,
        "pii_summary":        pii_summary,
        "detected_language":  detected_lang,
        "legal_context":      legal_context,       # ✅ NOW EXPOSED
        "retrieval_count":    retrieval_count,      # ✅ NOW EXPOSED
    }