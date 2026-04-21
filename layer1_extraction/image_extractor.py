"""
layer1_extraction/image_extractor.py
Extract text from image files via Sarvam Vision OCR.
Supports: PNG, JPG, JPEG, TIFF, BMP, WEBP
"""

from pathlib import Path
from layer1_extraction.sarvam_extractor import extract_with_sarvam
from utils.logger import get_logger
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

logger = get_logger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}


def extract_image_text(file_path: str) -> dict:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in IMAGE_EXTENSIONS:
        return {
            "text": "",
            "pages": 0,
            "success": False,
            "error": f"Unsupported image format: {ext}. Supported: {', '.join(sorted(IMAGE_EXTENSIONS))}",
            "extraction_method": "none"
        }

    try:
        size_kb = path.stat().st_size // 1024
        logger.info(f"Image extraction: {path.name} ({size_kb}KB)")

        #    Skip very small images (avoid heavy OCR)
        if size_kb < 10:
            return {
                "text": "",
                "pages": 0,
                "success": True,
                "error": None,
                "extraction_method": "skipped_small_image"
            }

        #    Run OCR
        result = extract_with_sarvam(file_path=file_path)

        #    Skip useless output
        if not result.get("text") or len(result["text"].strip()) < 5:
            return {
                "text": "",
                "pages": 1,
                "success": True,
                "error": None,
                "extraction_method": "empty_ocr"
            }

        result["extraction_method"] = "sarvam_vision_image"
        return result

    except Exception as e:
        return {
            "text": "",
            "pages": 0,
            "success": False,
            "error": str(e),
            "extraction_method": "image_error"
        }