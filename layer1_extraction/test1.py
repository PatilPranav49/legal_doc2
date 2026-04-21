import pdfplumber

with pdfplumber.open("C:\\Users\\itspr\\Downloads\\marathi_test.pdf") as pdf:
    text = ""
    for p in pdf.pages:
        text += p.extract_text() or ""

print(text[:500])