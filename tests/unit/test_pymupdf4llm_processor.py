import pymupdf
import pytest

from app.domain.errors import CorruptPdfError, ExtractionError
from app.infrastructure.processor.pymupdf4llm_processor import Pymupdf4LlmProcessor


def _make_pdf(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    return document.tobytes()


@pytest.mark.asyncio
async def test_extract_returns_text_and_page_count() -> None:
    processor = Pymupdf4LlmProcessor()

    content = await processor.extract(_make_pdf("Hello PDF"))

    assert "Hello PDF" in content.text
    assert content.page_count == 1


@pytest.mark.asyncio
async def test_extract_counts_multiple_pages() -> None:
    document = pymupdf.open()
    for _ in range(3):
        page = document.new_page()
        page.insert_text((72, 72), "page")
    processor = Pymupdf4LlmProcessor()

    content = await processor.extract(document.tobytes())

    assert content.page_count == 3


@pytest.mark.asyncio
async def test_extract_rejects_non_pdf_bytes() -> None:
    processor = Pymupdf4LlmProcessor()

    with pytest.raises(CorruptPdfError):
        await processor.extract(b"definitely not a pdf")


@pytest.mark.asyncio
async def test_extract_surfaces_processor_failure_as_extraction_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.infrastructure.processor.pymupdf4llm_processor as processor_module

    def broken_extract(*args, **kwargs) -> None:
        raise RuntimeError("layout engine exploded")

    monkeypatch.setattr(processor_module.pymupdf4llm, "to_markdown", broken_extract)

    processor = Pymupdf4LlmProcessor()

    with pytest.raises(ExtractionError):
        await processor.extract(_make_pdf("Hello PDF"))
