from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from contextlib import asynccontextmanager
import logging

from app.core.config import get_settings
from app.api.v1.router import router as api_v1_router
from app.core.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting CoinDCX Algo Trading Application")
    
    # Initialize database
    init_db()
    
    # Initialize market data service on startup
    from app.api.v1.endpoints.market_data import get_market_service
    market_service = get_market_service()
    await market_service.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down CoinDCX Algo Trading Application")
    await market_service.stop()

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title="CoinDCX Algorithmic Trading API",
        description="Professional algorithmic trading platform for CoinDCX exchange",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(api_v1_router, prefix="/api/v1")
    
    return app

# Create app instance
app = create_app()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "CoinDCX Algorithmic Trading API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "CoinDCX Algo Trading API is running"
    }

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
