import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.endpoints import router as api_router
from app.utils.data_loader import load_all_data

logger = logging.getLogger("gatis")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles lifecycle events including startup dataset loading."""
    logger.info("Initializing Global Agronomy & Trade Intelligence System (GATIS)...")
    try:
        load_all_data()
        logger.info("System boot and dataset loading complete.")
    except Exception as e:
        logger.critical(f"Failed to bootstrap GATIS memory database: {e}", exc_info=True)
    yield
    logger.info("Shutting down GATIS backend services...")

# Initialize FastAPI App
app = FastAPI(
    title="GATIS — Crop & Trade Intelligence",
    description="Professional refactored backend for the Global Agronomy & Trade Intelligence System",
    version="2.0.0",
    lifespan=lifespan
)


app.mount(
    "/static",
    StaticFiles(directory="frontend/static"),
    name="static"
)

# CORS setup for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Mount GATIS APIs router
app.include_router(api_router)

# Basic health check endpoint
@app.get("/health")
def health_check():
    """Confirms API status and server responsiveness."""
    return {"status": "healthy", "service": "GATIS-Backend-API"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting GATIS local server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
