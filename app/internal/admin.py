from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/")
async def update_admin():
    return {"message": "Admin getting schwifty"}
