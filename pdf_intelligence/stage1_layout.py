import fitz

def extract_layout(pdf_path):
    doc = fitz.open(pdf_path)
    words = []

    for page_num, page in enumerate(doc):
        for w in page.get_text("words"):
            x0, y0, x1, y1, text = w[:5]
            words.append({
                "text": text,
                "x0": x0,
                "x1": x1,
                "y": round(y0, 1),
                "page": page_num
            })

    return words
