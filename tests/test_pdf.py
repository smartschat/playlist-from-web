"""Tests for PDF text extraction."""

import fitz

from app.pdf import extract_text_from_pdf


def _create_test_pdf(text: str) -> bytes:
    """Create a simple PDF with the given text content."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_extract_text_from_simple_pdf() -> None:
    """Test basic text extraction from a single-page PDF."""
    text = "Artist - Song Title"
    pdf_bytes = _create_test_pdf(text)

    result = extract_text_from_pdf(pdf_bytes)

    assert "Artist" in result
    assert "Song Title" in result


def test_extract_text_from_multipage_pdf() -> None:
    """Test text extraction from a multi-page PDF."""
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Page 1: First Track")
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Page 2: Second Track")
    pdf_bytes = doc.tobytes()
    doc.close()

    result = extract_text_from_pdf(pdf_bytes)

    assert "First Track" in result
    assert "Second Track" in result


def test_extract_text_preserves_newlines() -> None:
    """Test that extracted text contains page separations."""
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Track A")
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Track B")
    pdf_bytes = doc.tobytes()
    doc.close()

    result = extract_text_from_pdf(pdf_bytes)

    # Pages should be separated
    assert "Track A" in result
    assert "Track B" in result
