class DomainError(Exception):
    status_code: int | None = 500
    title = "Internal Server Error"
    problem_type = "about:blank"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidPayloadError(DomainError):
    status_code = 400
    title = "Invalid Payload"
    problem_type = "/problems/invalid-payload"


class PayloadTooLargeError(DomainError):
    status_code = 413
    title = "Payload Too Large"
    problem_type = "/problems/payload-too-large"


class CorruptPdfError(DomainError):
    status_code = 422
    title = "Unprocessable Content"
    problem_type = "/problems/corrupt-pdf"


class ExtractionError(DomainError):
    status_code = 500
    title = "Extraction Failed"
    problem_type = "/problems/extraction-failed"


class CacheUnavailableError(DomainError):
    """Raised when the cache cannot be reached.

    Never mapped to an HTTP response: the service treats cache failures as
    non-fatal and proceeds with full processing.
    """

    status_code = None
    title = "Cache Unavailable"
    problem_type = "about:blank"
