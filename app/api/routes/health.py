from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", status_code=200)
async def health() -> dict[str, str]:
    return {"status": "ok"}
