import asyncio

import pymupdf
import pymupdf4llm

from app.domain.errors import CorruptPdfError, ExtractionError
from app.domain.models.extract_result import ExtractedContent


class Pymupdf4LlmProcessor:
    async def extract(self, pdf_bytes: bytes) -> ExtractedContent:
        text, page_count = await asyncio.to_thread(self._extract_sync, pdf_bytes)
        return ExtractedContent(text=text, page_count=page_count)

    def _extract_sync(self, pdf_bytes: bytes) -> tuple[str, int]:
        try:
            document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except (pymupdf.FileDataError, pymupdf.EmptyFileError) as exc:
            raise CorruptPdfError("payload is not a readable PDF") from exc
        try:
            text = pymupdf4llm.to_markdown(doc=document)
        except Exception as exc:
            raise ExtractionError("PDF processing failed") from exc
        return text, document.page_count
