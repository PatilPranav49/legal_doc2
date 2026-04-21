import sys
import os

PIPELINE_PATH = os.path.abspath("../legal_doc_analyzer_fixed")
sys.path.append(PIPELINE_PATH)

from layer1_extraction.image_extractor import extract_image_text
from layer1_extraction.sarvam_extractor import extract_with_sarvam


def extract_text(file_path, filename):
    filename = filename.lower()

    try:
        # 🖼️ IMAGE
        if filename.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")):
            result = extract_image_text(file_path)
            return result.get("text", "")

        # 📄 PDF → ALWAYS OCR here (no recursion)
        elif filename.endswith(".pdf"):
            res = extract_with_sarvam(file_path=file_path)
            return res.get("text", "")

        else:
            return "Unsupported file type"

    except Exception as e:
        return f"OCR failed: {str(e)}"