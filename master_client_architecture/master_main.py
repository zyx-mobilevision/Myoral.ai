"""
Master Server Main Application
Entry point for the MyOral Master Server - Analytics and monitoring

This server handles:
- Analytics endpoints for aggregated data
- Client server management
- Sync monitoring and logging
- API key management
- System health monitoring
"""

import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our API design
from api.master_server import MasterServerAPIDesign
from database.manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("master_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("🚀 Starting MyOral Master Server")
    
    # Initialize database
    try:
        db_manager = DatabaseManager()
        logger.info("✅ Database initialized successfully")
        
        # Store database manager in app state
        app.state.db_manager = db_manager
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # Verify environment configuration
    required_env_vars = [
        "MASTER_DB_HOST", "MASTER_DB_PORT", "MASTER_DB_NAME",
        "MASTER_DB_USER", "MASTER_DB_PASS", "MASTER_SERVER_SALT"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.warning(f"⚠️  Missing environment variables: {missing_vars}")
    
    logger.info("🟢 Master Server startup complete")
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down MyOral Master Server")
    
    # Cleanup database connections
    if hasattr(app.state, 'db_manager'):
        logger.info("🔒 Closing database connections")
    
    logger.info("✅ Master Server shutdown complete")


def create_master_app() -> FastAPI:
    """
    Create and configure the master server FastAPI application
    
    Returns:
        FastAPI: Configured application instance
    """
    
    # Create the main FastAPI app with lifespan manager
    app = FastAPI(
        title="MyOral Master Server",
        description="Analytics and monitoring API for MyOral multi-client architecture",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React development server
            "http://localhost:8000",  # Client server
            "https://myoral.com",     # Production frontend
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Create and mount the API design
    master_api = MasterServerAPIDesign()
    
    # Mount all routes from the API design
    app.mount("/", master_api.get_app())
    
    # Add global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else "Internal server error"
            }
        )
    
    # Add additional health endpoints
    @app.get("/api/health/detailed", tags=["Health"])
    async def detailed_health_check():
        """Detailed health check with system status"""
        try:
            db_manager = app.state.db_manager
            connection_status = db_manager.get_connection_status()
            system_health = db_manager.get_system_health()
            
            return {
                "status": "healthy",
                "timestamp": "2025-08-21T00:00:00Z",
                "version": "1.0.0",
                "database": {
                    "status": "connected",
                    "connections": connection_status
                },
                "system": system_health,
                "environment": os.getenv("ENVIRONMENT", "development")
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": "2025-08-21T00:00:00Z"
                }
            )
    
    return app


# Create the application instance
app = create_master_app()


def main():
    """
    Main entry point for running the master server
    """
    # Get configuration from environment
    host = os.getenv("MASTER_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MASTER_SERVER_PORT", 8001))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"🌐 Starting Master Server on {host}:{port}")
    logger.info(f"📚 API documentation available at http://{host}:{port}/docs")
    
    # Run the server
    uvicorn.run(
        "master_main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug",
        access_log=True,
        loop="asyncio"
    )


if __name__ == "__main__":
    main()
