"""
Extracts keywords from a Word document.

Expected format: one keyword or phrase per line/paragraph in the .docx.
Blank paragraphs and lines starting with "# " (comments) are ignored.

Example keywords.docx content:
    Whoa Dough
    protein cookie dough
    healthy snacks
    #WhoaDough
"""
from pathlib import Path
from docx import Document


def extract_keywords(docx_path: str) -> list[str]:
    """
    Read a .docx file and return a deduplicated list of non-empty keyword
    strings, one per paragraph, preserving the order they appear in the doc.
    """
    path = Path(docx_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Keywords document not found at: {docx_path}\n"
            f"Create it and list one keyword/phrase per line."
        )

    doc = Document(str(path))
    keywords: list[str] = []
    seen = set()

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        # Only treat "# " (hash + space) as a comment marker, so hashtag
        # keywords like "#WhoaDough" are never mistaken for comments.
        if text.startswith("# "):
            continue
        key = text.lower()
        if key not in seen:
            seen.add(key)
            keywords.append(text)

    if not keywords:
        raise ValueError(
            f"No keywords found in {docx_path}. "
            f"Add at least one keyword per paragraph."
        )

    return keywords


if __name__ == "__main__":
    # Quick manual test: python keyword_extractor.py path/to/keywords.docx
    import sys
    test_path = sys.argv[1] if len(sys.argv) > 1 else "./data/keywords.docx"
    for kw in extract_keywords(test_path):
        print(kw)