from pathlib import Path
from layer1_extraction.sarvam_extractor import extract_with_sarvam
from layer1_extraction.image_extractor import extract_image_text
from layer1_extraction.docx_extractor import extract_docx_text
from layer1_extraction.pdf_extractor import extract_pdf_text
from utils.logger import get_logger

logger = get_logger(__name__)


class DocumentExtractor:

    SUPPORTED_EXTENSIONS = {
        ".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif",
        ".bmp", ".webp", ".docx", ".txt"
    }

    def extract(self, file_path: str, language_hint: str = None) -> dict:
        path = Path(file_path)
        ext = path.suffix.lower()

        if not path.exists():
            return self._error(f"File not found: {file_path}")

        if ext not in self.SUPPORTED_EXTENSIONS:
            return self._error(f"Unsupported file type: {ext}")

        if ext == ".txt":
            res = self._extract_txt(file_path)
            res["extraction_method"] = "direct_read"
            return res

        elif ext == ".docx":
            res = extract_docx_text(file_path)
            res["extraction_method"] = "docx"
            return res

        elif ext in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}:
            res = extract_image_text(file_path)
            res["extraction_method"] = "image_ocr"
            return res
        elif ext == ".pdf":
            res = extract_pdf_text(file_path)

            if res.get("likely_scanned", False):
                try:
                    from pdf2image import convert_from_path
                    import pytesseract
                    from PIL import Image

                    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                    poppler_path = r"C:\poppler\poppler-25.12.0\Library\bin"

                    images = convert_from_path(
                        file_path,
                        dpi=300,
                        poppler_path=poppler_path
                    )

                    full_text = ""
                    for img in images:
                        text = pytesseract.image_to_string(
                            img,
                            lang="mar+hin+eng",
                            config="--oem 3 --psm 3"
                        )
                        full_text += text + "\n"

                    return {
                        "text": full_text.strip(),
                        "pages": len(images),
                        "success": True,
                        "likely_scanned": True,
                        "error": None,
                        "extraction_method": "tesseract_ocr"
                    }

                except Exception as e:
                    return self._error(str(e))

            return res
        
        return self._error("Unknown file type")

    def _extract_txt(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            return {
                "text": text,
                "pages": 1,
                "success": True,
                "error": None,
            }
        except Exception as e:
            return self._error(str(e))

    def _error(self, msg):
        return {
            "text": "",
            "pages": 0,
            "success": False,
            "error": msg,
            "extraction_method": "none",
        }