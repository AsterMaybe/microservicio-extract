from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ExtractedContent(BaseModel):
    text: str
    page_count: int = Field(ge=0)


class ExtractionResult(BaseModel):
    document_id: str | None = None
    filename: str | None = None
    text: str
    page_count: int = Field(ge=0)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
