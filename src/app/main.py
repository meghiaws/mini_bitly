from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api.v1 import urls


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A minimal URL shortener service",
)

# CORS decorators
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(urls.router, tags=["URLs"])


@app.get("/")
async def root():
    return {
        "message": "Mini Bitly URL Shortener",
        "version": settings.APP_VERSION,
        "status": "healthy"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
