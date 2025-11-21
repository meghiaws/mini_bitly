from fastapi import APIRouter

from .urls import router as urls_router

router = APIRouter(prefix="/v1")

router.include_router(urls_router)
