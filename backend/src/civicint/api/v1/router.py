from fastapi import APIRouter

from civicint.api.v1.admin import router as admin_router
from civicint.api.v1.cases import router as cases_router
from civicint.api.v1.municipalities import router as municipalities_router

router = APIRouter()
router.include_router(cases_router)
router.include_router(municipalities_router)
router.include_router(admin_router)


@router.get("/ping")
async def ping():
    return {"message": "pong"}
