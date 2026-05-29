from fastapi import APIRouter

from civicint.api.v1.cases import router as cases_router

router = APIRouter()
router.include_router(cases_router)


@router.get("/ping")
async def ping():
    return {"message": "pong"}
