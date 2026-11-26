"""Safe, size-capped extraction for PDF, DOCX and UTF-8 TXT."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from pypdf import Configuration, PdfReader, apply_configuration

MAX_FILE_BYTES = 3 * 1024 * 1024
MAX_TEXT_CHARS = 100_000
MAX_EXPANDED_BYTES = 20 * 1024 * 1024
PDF_LIMITS = Configuration(
    maximum_declared_stream_length=MAX_EXPANDED_BYTES,
    zlib_maximum_output_length=MAX_EXPANDED_BYTES,
    array_based_stream_maximum_output_length=MAX_EXPANDED_BYTES,
    page_tree_maximum_entries=1000,
    page_tree_maximum_page_entries=5000,
    xform_maximum_invocations_per_extraction=100,
    jbig2dec_binary=None,
)
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


def extract_document(filename: str, payload: bytes) -> tuple[str, str]:
    ext = Path(filename).suffix.lower()
    if ext not in MIME_TYPES:
        raise ValueError("รองรับเฉพาะ PDF, DOCX และ TXT")
    if not payload or len(payload) > MAX_FILE_BYTES:
        raise ValueError("ไฟล์ต้องมีขนาดมากกว่า 0 และไม่เกิน 3 MB")

    try:
        if ext == ".txt":
            text = payload.decode("utf-8-sig")
            if "\x00" in text:
                raise ValueError("TXT ต้องเป็นข้อความ UTF-8")
        elif ext == ".pdf":
            if not payload.startswith(b"%PDF-"):
                raise ValueError("รูปแบบไฟล์ PDF ไม่ถูกต้อง")
            with apply_configuration(PDF_LIMITS):
                reader = PdfReader(BytesIO(payload), root_object_recovery_limit=1000,
                                   xref_stream_maximum_entries=100_000)
                if reader.is_encrypted:
                    raise ValueError("ไม่รองรับ PDF ที่เข้ารหัสหรือใส่รหัสผ่าน")
                if len(reader.pages) > 40:
                    raise ValueError("PDF ต้องไม่เกิน 40 หน้า")
                parts, remaining = [], MAX_TEXT_CHARS
                for page in reader.pages:
                    piece = (page.extract_text() or "")[:remaining]
                    parts.append(piece)
                    remaining -= len(piece) + 1
                    if remaining <= 0:
                        break
                text = "\n".join(parts)
        else:
            with ZipFile(BytesIO(payload)) as archive:
                parts = archive.infolist()
                if len(parts) > 500 or sum(part.file_size for part in parts) > MAX_EXPANDED_BYTES:
                    raise ValueError("ไฟล์ DOCX มีข้อมูลมากเกินขีดจำกัด")
            doc = Document(BytesIO(payload))
            paragraphs = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    paragraphs.append(" | ".join(cell.text for cell in row.cells))
            text = "\n".join(paragraphs)
    except UnicodeError as error:
        raise ValueError("TXT ต้องเป็นข้อความ UTF-8") from error
    except ValueError:
        raise
    except Exception as error:
        raise ValueError("อ่านไฟล์ไม่ได้ ตรวจสอบประเภทไฟล์และลองบันทึกต้นฉบับใหม่") from error

    return text.replace("\x00", "")[:MAX_TEXT_CHARS], MIME_TYPES[ext]
