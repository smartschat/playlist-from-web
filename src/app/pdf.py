"""PDF text extraction using PyMuPDF."""

import fitz


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text content from a PDF file.

    Args:
        pdf_bytes: Raw PDF file bytes.

    Returns:
        Extracted text content from all pages, joined with newlines.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)
