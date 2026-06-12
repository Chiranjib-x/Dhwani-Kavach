from fastapi import APIRouter
from ml.liveness import generate_challenge

router = APIRouter()


@router.get("/challenge")
async def get_challenge():
    """Return a spoken-digit liveness challenge for the caller."""
    return generate_challenge()
