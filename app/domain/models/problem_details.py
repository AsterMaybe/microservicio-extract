from pydantic import BaseModel, Field


class ProblemDetails(BaseModel):
    type: str = Field(default="about:blank")
    title: str
    status: int
    detail: str
    instance: str | None = None
