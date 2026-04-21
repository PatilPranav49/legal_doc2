from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from pathlib import Path
from PIL import Image
import tempfile
import os
import pytesseract
import cv2
import numpy as np

# ✅ FIX: Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ✅ FIX: Poppler path
os.environ["PATH"] += os.pathsep + r"C:\poppler\poppler-25.12.0\Library\bin"

# ✅ Use Hindi model (better for Marathi + Hindi)
ocr = PaddleOCR(use_angle_cls=True, lang='hi')


def safe_extract_text(paddle_result):
    extracted = []

    if not paddle_result:
        return ""

    for block in paddle_result:
        if not isinstance(block, list):
            continue

        for line in block:
            if (
                isinstance(line, list) and
                len(line) >= 2 and
                isinstance(line[1], (list, tuple)) and
                len(line[1]) >= 1
            ):
                text_part = line[1][0]
                if isinstance(text_part, str) and text_part.strip():
                    extracted.append(text_part.strip())

    return "\n".join(extracted)


def is_garbage(text):
    if not text:
        return True

    hindi_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    return hindi_chars < len(text) * 0.3


def extract_with_sarvam(file_path=None, file_bytes=None, file_ext=".pdf"):
    try:
        if file_path:
            ext = Path(file_path).suffix.lower()

            # ===================== PDF =====================
            if ext == ".pdf":
                images = convert_from_path(
                    file_path,
                    dpi=350,  #    FIX: higher DPI
                    poppler_path=r"C:\poppler\poppler-25.12.0\Library\bin"
                )

                text = ""
                num_pages = len(images)

                for img in images:
                    try:
                        img_np = np.array(img)

                   
                        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                        gray = cv2.convertScaleAbs(gray, alpha=2.5, beta=40)
                        gray = cv2.GaussianBlur(gray, (3, 3), 0)

                        processed = cv2.adaptiveThreshold(
                            gray, 255,
                            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                            cv2.THRESH_BINARY,
                            31, 2
                        )

                        # Paddle attempt
                        paddle_result = ocr.ocr(processed, cls=True)
                        paddle_text = safe_extract_text(paddle_result)

                        #fallback to raw
                        if is_garbage(paddle_text):
                            paddle_result_raw = ocr.ocr(img_np, cls=True)
                            paddle_text_raw = safe_extract_text(paddle_result_raw)

                            if len(paddle_text_raw) > len(paddle_text):
                                paddle_text = paddle_text_raw

                        #  Tesseract fallback
                        if is_garbage(paddle_text):
                            tess_text = pytesseract.image_to_string(
                                processed,
                                lang="mar+hin+eng",
                                config="--oem 3 --psm 11"
                            )

                            if not tess_text.strip():
                                tess_text = pytesseract.image_to_string(
                                    img_np,
                                    lang="mar+hin+eng",
                                    config="--oem 3 --psm 11"
                                )

                            text += tess_text + "\n"
                        else:
                            text += paddle_text + "\n"

                    except Exception:
                        continue

            # ===================== IMAGE =====================
            else:
                img = cv2.imread(file_path)

                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                gray = cv2.convertScaleAbs(gray, alpha=2, beta=20)
                gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                gray = cv2.medianBlur(gray, 3)

                text = pytesseract.image_to_string(
                    gray,
                    lang="mar+hin+eng",
                    config="--oem 3 --psm 11"
                )

                num_pages = 1

        elif file_bytes:
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            result = extract_with_sarvam(tmp_path)
            os.unlink(tmp_path)
            return result

        else:
            return _err("No file provided")

        return {
            "text": text.strip(),
            "pages": num_pages,
            "success": True,
            "error": None,
            "extraction_method": "hybrid_ocr"
        }

    except Exception as e:
        return _err(str(e))


def _err(msg):
    return {
        "text": "",
        "pages": 0,
        "success": False,
        "error": msg,
        "extraction_method": "ocr_error"
    }