from io import BytesIO

import pytest
from docx import Document
from pypdf import PdfWriter

from file_utils import MAX_FILE_BYTES, MAX_TEXT_CHARS, extract_document


def test_thai_text_and_limit():
    content, mime = extract_document("ตัวอย่าง.TXT", ("ก" * (MAX_TEXT_CHARS + 10)).encode("utf-8-sig"))
    assert content == "ก" * MAX_TEXT_CHARS
    assert mime == "text/plain"


def test_docx_paragraph_and_table():
    doc = Document()
    doc.add_paragraph("รายงานตัวอย่าง")
    doc.add_table(rows=1, cols=1).cell(0, 0).text = "วันประชุม"
    buffer = BytesIO()
    doc.save(buffer)
    text, mime = extract_document("รายงาน.docx", buffer.getvalue())
    assert text == "รายงานตัวอย่าง\nวันประชุม"
    assert mime.endswith("wordprocessingml.document")


def test_pdf_scanned_placeholder_and_page_limit():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = BytesIO()
    writer.write(buffer)
    assert extract_document("ตัวอย่าง.pdf", buffer.getvalue()) == ("", "application/pdf")

    for _ in range(40):
        writer.add_blank_page(width=100, height=100)
    buffer = BytesIO()
    writer.write(buffer)
    with pytest.raises(ValueError, match="40"):
        extract_document("หลายหน้า.pdf", buffer.getvalue())


@pytest.mark.parametrize(("name", "data"), [
    ("test.exe", b"sample"), ("empty.txt", b""), ("fake.pdf", b"sample"),
    ("fake.docx", b"sample"), ("invalid.txt", b"\xff"), ("binary.txt", b"\x00"),
    ("oversized.txt", b"a" * (MAX_FILE_BYTES + 1)),
])
def test_rejects_unsupported_or_invalid_inputs(name, data):
    with pytest.raises(ValueError):
        extract_document(name, data)
