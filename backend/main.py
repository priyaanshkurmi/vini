import logging
import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.router import router
from api.voice_router import voice_router
from api.websocket import ws_router
from middleware import RateLimitMiddleware

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

app = FastAPI(title="Vini Backend")

# Parse allowed origins from env (comma-separated)
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:8080"
).split(",")

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(voice_router)
app.include_router(ws_router)


@app.on_event("startup")
async def startup():
    logger = logging.getLogger("vini")
    logger.info("Vini backend starting up...")
    try:
        from services.voice_loop import voice_loop
        loop = asyncio.get_event_loop()
        voice_loop.start(loop)
        logger.info("Voice loop started.")
    except Exception as e:
        logger.error(f"Failed to start voice loop: {e}")


@app.get("/")
async def root():
    return {"status": "Vini is alive", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        from services.llm import get_llm_provider
        llm = get_llm_provider()
        return {
            "status": "healthy",
            "service": "vini-backend",
            "llm_provider": type(llm).__name__,
        }
    except Exception as e:
        logger = logging.getLogger("vini")
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }, 503
