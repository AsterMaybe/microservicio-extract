from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.models.extract_request import ExtractionRequest
from app.domain.models.extract_result import ExtractedContent, ExtractionResult
from app.domain.models.problem_details import ProblemDetails


def test_extraction_request_parses_minimal_payload() -> None:
    request = ExtractionRequest(pdf_base64="aGVsbG8=")

    assert request.pdf_base64 == "aGVsbG8="
    assert request.document_id is None
    assert request.filename is None


def test_extraction_request_carries_optional_metadata() -> None:
    request = ExtractionRequest(
        document_id="doc-123",
        filename="report.pdf",
        pdf_base64="aGVsbG8=",
    )

    assert request.document_id == "doc-123"
    assert request.filename == "report.pdf"


def test_extraction_request_requires_pdf_base64() -> None:
    with pytest.raises(ValidationError):
        ExtractionRequest()  # type: ignore[call-arg]


def test_extraction_request_rejects_empty_base64() -> None:
    with pytest.raises(ValidationError):
        ExtractionRequest(pdf_base64="")


def test_extracted_content_holds_text_and_page_count() -> None:
    content = ExtractedContent(text="hello", page_count=3)

    assert content.text == "hello"
    assert content.page_count == 3


def test_extracted_content_rejects_negative_page_count() -> None:
    with pytest.raises(ValidationError):
        ExtractedContent(text="hello", page_count=-1)


def test_extraction_result_rejects_bad_checksum() -> None:
    with pytest.raises(ValidationError):
        ExtractionResult(
            text="hello",
            page_count=1,
            checksum="not-a-sha256",
        )


def test_extraction_result_round_trips_through_json() -> None:
    created_at = datetime.now(UTC)
    result = ExtractionResult(
        document_id="doc-1",
        filename="f.pdf",
        text="hello",
        page_count=2,
        checksum="a" * 64,
        created_at=created_at,
    )

    restored = ExtractionResult.model_validate_json(result.model_dump_json())

    assert restored == result
    assert restored.created_at == created_at


def test_extraction_result_defaults_created_at_to_utc_now() -> None:
    result = ExtractionResult(text="h", page_count=1, checksum="a" * 64)

    assert result.created_at.tzinfo == UTC


def test_problem_details_has_rfc9457_defaults() -> None:
    problem = ProblemDetails(title="Bad Request", status=400, detail="bad base64")

    assert problem.type == "about:blank"
    assert problem.status == 400
    assert problem.title == "Bad Request"
    assert problem.detail == "bad base64"
    assert problem.instance is None
