import pdfplumber

BROKEN_DEVANAGARI_FONTS = (
    'DVOT', 'DVTT', 'DVES', 'SHREE', 'SHUSHA', 'KIRAN',
    'BALBHARATI', 'BALBHARATIDEV', 'SUREKH', 'SARAS',
    'AKRUTI', 'KRUTI', 'WALKMAN', 'YOGESH'
)


def has_legacy_font(page) -> bool:
    seen = set()
    for char in page.chars[:200]:
        fname = char.get('fontname', '').upper()
        seen.add(fname)
    for fname in seen:
        for broken in BROKEN_DEVANAGARI_FONTS:
            if broken in fname:
                return True
    return False


def extract_pdf_text(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            text_parts = []
            pages = len(pdf.pages)
            empty_pages = 0
            force_ocr = False

            for page in pdf.pages:
                try:
                    if not force_ocr and has_legacy_font(page):
                        force_ocr = True

                    if force_ocr:
                        empty_pages += 1
                        continue

                    page_text = page.extract_text(
                        x_tolerance=3,
                        y_tolerance=3,
                    )

                    if not page_text or len(page_text.strip()) < 20:
                        empty_pages += 1
                    else:
                        text_parts.append(page_text.strip())

                except Exception:
                    empty_pages += 1

        text = "\n".join(text_parts).strip()

        if force_ocr or not text or (empty_pages / max(pages, 1)) > 0.3:
            return {
                "text": "",
                "pages": pages,
                "success": True,
                "likely_scanned": True,
                "error": None,
                "extraction_method": "pdf_legacy_font_ocr"
            }

        return {
            "text": text,
            "pages": pages,
            "success": True,
            "likely_scanned": False,
            "error": None,
            "extraction_method": "pdfplumber"
        }

    except Exception as e:
        return {
            "text": "",
            "pages": 0,
            "success": False,
            "likely_scanned": True,
            "error": str(e),
            "extraction_method": "pdf_error"
        }