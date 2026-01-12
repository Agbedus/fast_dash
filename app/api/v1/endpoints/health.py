from fastapi import APIRouter
from typing import Any

router = APIRouter()

@router.get("", response_model=dict[str, Any])
def health_check() -> Any:
    """
    Health check endpoint.
    """
    return {"status": "ok"}
