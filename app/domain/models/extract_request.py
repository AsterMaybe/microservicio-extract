from pydantic import BaseModel, ConfigDict, Field


class ExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str | None = None
    filename: str | None = None
    pdf_base64: str = Field(min_length=1)
