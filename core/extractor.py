import pytesseract
from PIL import Image
import io
import re
import numpy as np
import cv2
from pdf2image import convert_from_bytes
from paddleocr import PaddleOCR
from core.preprocess import preprocess_image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Hindi model covers Devanagari script — works for both Hindi and Marathi
ocr = PaddleOCR(use_angle_cls=True, lang='hi')


def is_garbage(text):
    if not text or len(text.strip()) < 20:
        return True

    # Allow English, Devanagari, digits and common punctuation
    # Penalise only true garbage symbols
    bad_chars = sum(
        1 for c in text
        if not c.isalnum()
        and not ('\u0900' <= c <= '\u097F')  # Devanagari (Hindi + Marathi)
        and c not in " .,\n।-:/()"
    )
    ratio = bad_chars / max(len(text), 1)

    return ratio > 0.35


def paddle_extract(image):
    try:
        result = ocr.ocr(image)
    except:
        return ""

    text = ""

    if not result:
        return ""

    for line in result:
        if not line:
            continue

        for word in line:
            try:
                if len(word) >= 2 and word[1]:
                    text += word[1][0] + " "
            except:
                continue

    return text.strip()


def tesseract_extract(image):
    return pytesseract.image_to_string(
        image,
        lang="hin+mar+eng",  # Hindi + Marathi + English
        config="--oem 3 --psm 3"  # psm 3 = fully automatic, handles multi-column
    )


def process_image(image):
    processed = preprocess_image(image)

    def safe_text(text):
        return text if isinstance(text, str) else ""

    def score(text):
        text = safe_text(text)

        if not text:
            return 0

        length = len(text)
        if length == 0:
            return 0

        # Count valid characters across all three scripts
        devanagari = len(re.findall(r'[\u0900-\u097F]', text))
        english    = len(re.findall(r'[a-zA-Z]', text))
        digits     = len(re.findall(r'[0-9]', text))

        # Garbage = anything not in any expected script or punctuation
        garbage = len(re.findall(r'[^a-zA-Z0-9\u0900-\u097F\s.,।\-:\/()]', text))

        valid = devanagari + english + digits
        return (valid - garbage * 2) / length

    # Run both OCR engines
    try:
        tess_text = safe_text(tesseract_extract(processed))
    except:
        tess_text = ""

    try:
        paddle_text = safe_text(paddle_extract(processed))
    except:
        paddle_text = ""

    # Pick whichever engine gave cleaner output
    tess_score   = score(tess_text)
    paddle_score = score(paddle_text)

    return tess_text if tess_score >= paddle_score else paddle_text


def extract_text(file_bytes, filename):
    filename = filename.lower()
    final_text = ""

    try:
        if filename.endswith(".pdf"):
            images = convert_from_bytes(file_bytes, dpi=300)

            for img in images:
                text = process_image(img)
                final_text += text + "\n"

        else:
            image = Image.open(io.BytesIO(file_bytes))
            final_text = process_image(image)

        return final_text.strip() if isinstance(final_text, str) else ""

    except Exception as e:
        return f"OCR failed: {str(e)}"