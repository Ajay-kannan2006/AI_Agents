from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config.settings import settings
from config.logging_config import logger
from src.db.database import init_db
from src.api.routes import router as research_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Research Agent Application...")
    await init_db()
    logger.info("Database schemas initialized.")
    yield
    logger.info("Shutting down Research Agent Application...")

app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous Research Agent for Multi-Source Information Gathering, Academic Search, Document Summarization, Citation Engine, and PPT Generation.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
