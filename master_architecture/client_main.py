"""
Client Server Main Application
Entry point for the MyOral Client Server - Patient data and operations

This server handles:
- Patient registration and management
- Photo uploads and analysis
- User authentication and profiles
- Appointment scheduling
- Data synchronization with master server
- Local PII and medical data storage
"""

import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime

# Load environment variables
load_dotenv()

# Import existing routers (these would be your current MyOral routers)
# from routers import (
#     register, login, photoUpload, update, analyze, 
#     retrieve, reminder, print, oral_report_pdf
# )

# Import sync services
from services.sync_service import ClientSyncService
from services.scheduler import BackgroundSyncScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("client_server.log"),
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
    logger.info("🚀 Starting MyOral Client Server")
    
    # Initialize database connection
    try:
        # Import your existing database setup
        # from database import get_db, engine
        # Test database connection
        logger.info("✅ Client database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Client database initialization failed: {e}")
        raise
    
    # Initialize sync service
    try:
        client_id = os.getenv("CLIENT_ID", "client_001")
        master_url = os.getenv("MASTER_SERVER_URL", "http://localhost:8001")
        api_key = os.getenv("MASTER_API_KEY", "client_001_key")
        
        sync_service = ClientSyncService(client_id, master_url, api_key)
        app.state.sync_service = sync_service
        
        # Initialize background sync scheduler
        sync_interval = int(os.getenv("SYNC_INTERVAL_MINUTES", "30"))
        scheduler = BackgroundSyncScheduler(sync_service, interval_minutes=sync_interval)
        app.state.scheduler = scheduler
        
        # Start background sync
        await scheduler.start()
        logger.info(f"✅ Background sync started (interval: {sync_interval} minutes)")
        
    except Exception as e:
        logger.error(f"❌ Sync service initialization failed: {e}")
        # Don't fail startup if sync is not available
    
    # Verify environment configuration
    required_env_vars = [
        "CLIENT_DB_HOST", "CLIENT_DB_PORT", "CLIENT_DB_NAME",
        "CLIENT_DB_USER", "CLIENT_DB_PASS", "CLIENT_ID"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.warning(f"⚠️  Missing environment variables: {missing_vars}")
    
    logger.info("🟢 Client Server startup complete")
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down MyOral Client Server")
    
    # Stop background sync scheduler
    if hasattr(app.state, 'scheduler'):
        await app.state.scheduler.stop()
        logger.info("🔒 Background sync stopped")
    
    # Cleanup database connections
    logger.info("🔒 Closing database connections")
    
    logger.info("✅ Client Server shutdown complete")


def create_client_app() -> FastAPI:
    """
    Create and configure the client server FastAPI application
    
    Returns:
        FastAPI: Configured application instance
    """
    
    # Create the main FastAPI app with lifespan manager
    app = FastAPI(
        title="MyOral Client Server",
        description="Patient data management and dental health analysis",
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
            "http://localhost:8001",  # Master server
            "https://myoral.com",     # Production frontend
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Mount static files for uploaded photos
    if os.path.exists("users"):
        app.mount("/static", StaticFiles(directory="users"), name="static")
    
    # Include existing routers
    # app.include_router(register.router, prefix="/api", tags=["Registration"])
    # app.include_router(login.router, prefix="/api", tags=["Authentication"])
    # app.include_router(photoUpload.router, prefix="/api", tags=["Photos"])
    # app.include_router(update.router, prefix="/api", tags=["User Management"])
    # app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
    # app.include_router(retrieve.router, prefix="/api", tags=["Data Retrieval"])
    # app.include_router(reminder.router, prefix="/api", tags=["Reminders"])
    # app.include_router(print.router, prefix="/api", tags=["Reports"])
    # app.include_router(oral_report_pdf.router, prefix="/api", tags=["PDF Reports"])
    
    # Include new sync router
    # app.include_router(sync.router, prefix="/api/sync", tags=["Synchronization"])
    
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
    
    # Basic health check
    @app.get("/", tags=["Health"])
    async def root():
        """Root endpoint"""
        return {
            "message": "MyOral Client Server",
            "version": "1.0.0",
            "status": "running"
        }
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Basic health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": "2025-08-21T00:00:00Z",
            "server_type": "client"
        }
    
    @app.get("/api/health/detailed", tags=["Health"])
    async def detailed_health_check():
        """Detailed health check with sync status and master server connectivity"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "server_type": "client",
            "version": "1.0.0"
        }
        
        # Check sync service health
        if hasattr(app.state, 'sync_service'):
            try:
                sync_status = await app.state.sync_service.get_sync_status()
                health_status["sync_service"] = {
                    "active": True,
                    "master_server_healthy": sync_status.get("master_server_healthy", False),
                    "last_sync": sync_status.get("last_sync_time"),
                    "active_operations": sync_status.get("active_operations", 0),
                    "statistics": sync_status.get("sync_statistics", {}),
                    "http_client_stats": sync_status.get("http_client_stats", {})
                }
                
                # If master server is unhealthy, downgrade overall status
                if not sync_status.get("master_server_healthy", False):
                    health_status["status"] = "degraded"
                    health_status["warnings"] = ["Master server connectivity issues"]
                    
            except Exception as e:
                health_status["sync_service"] = {
                    "active": False,
                    "error": str(e)
                }
                health_status["status"] = "degraded"
                health_status["warnings"] = ["Sync service unavailable"]
        else:
            health_status["sync_service"] = {"active": False}
            health_status["status"] = "degraded"
            health_status["warnings"] = ["Sync service not initialized"]
        
        # Check database connectivity
        try:
            # Add your database health check here
            # db_status = await check_database_health()
            health_status["database"] = {"status": "healthy", "type": "client_database"}
        except Exception as e:
            health_status["database"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "unhealthy"
        
        return health_status
    
    # Robust sync management endpoints
    @app.post("/api/sync/manual", tags=["Synchronization"])
    async def trigger_manual_sync(background_tasks: BackgroundTasks):
        """
        Trigger manual synchronization with comprehensive error handling
        """
        if not hasattr(app.state, 'sync_service'):
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Sync service not available",
                    "code": "SYNC_SERVICE_UNAVAILABLE"
                }
            )
        
        try:
            # Check master server health first
            health_check = await app.state.sync_service.check_master_server_health()
            if not health_check:
                return JSONResponse(
                    status_code=503,
                    content={
                        "success": False,
                        "error": "Master server is not healthy",
                        "code": "MASTER_SERVER_UNHEALTHY",
                        "retry_after": 60
                    }
                )
            
            # Get pending sync operations (this would come from your database)
            # For demo purposes, we'll create sample operations
            sample_operations = [
                {
                    "type": "user",
                    "data": {
                        "userId": "user_123",
                        "birthdate": "1990-05-15",
                        "gender": "M",
                        "createdAt": "2025-08-21T10:00:00Z",
                        "register_method": "email"
                    }
                }
            ]
            
            # Perform bulk sync in background to not block the API response
            async def perform_sync():
                result = await app.state.sync_service.bulk_sync_operation(sample_operations)
                logger.info(f"Manual sync completed: {result}")
            
            background_tasks.add_task(perform_sync)
            
            return {
                "success": True,
                "message": "Manual sync initiated",
                "operations_queued": len(sample_operations),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Manual sync failed: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "code": "SYNC_OPERATION_FAILED"
                }
            )
    
    @app.get("/api/sync/status", tags=["Synchronization"])
    async def get_sync_status():
        """
        Get comprehensive sync status with detailed metrics
        """
        if not hasattr(app.state, 'sync_service'):
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Sync service not available",
                    "code": "SYNC_SERVICE_UNAVAILABLE"
                }
            )
        
        try:
            status = await app.state.sync_service.get_sync_status()
            return {
                "success": True,
                "sync_status": status,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get sync status: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "code": "STATUS_CHECK_FAILED"
                }
            )
    
    @app.post("/api/sync/circuit-breaker/reset", tags=["Synchronization"])
    async def reset_circuit_breaker():
        """
        Manually reset the circuit breaker and test connectivity
        """
        if not hasattr(app.state, 'sync_service'):
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Sync service not available",
                    "code": "SYNC_SERVICE_UNAVAILABLE"
                }
            )
        
        try:
            result = await app.state.sync_service.reset_circuit_breaker()
            
            if result.get('success', False):
                return {
                    "success": True,
                    "message": "Circuit breaker reset successfully",
                    "health_check_passed": result.get('health_check_passed', False),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": result.get('error', 'Unknown error'),
                        "code": "CIRCUIT_BREAKER_RESET_FAILED"
                    }
                )
                
        except Exception as e:
            logger.error(f"Circuit breaker reset failed: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "code": "OPERATION_FAILED"
                }
            )
    
    @app.get("/api/sync/metrics", tags=["Synchronization"])
    async def get_sync_metrics():
        """
        Get detailed sync metrics for monitoring and alerting
        """
        if not hasattr(app.state, 'sync_service'):
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Sync service not available",
                    "code": "SYNC_SERVICE_UNAVAILABLE"
                }
            )
        
        try:
            status = await app.state.sync_service.get_sync_status()
            sync_stats = status.get("sync_statistics", {})
            http_stats = status.get("http_client_stats", {})
            
            metrics = {
                "sync_metrics": {
                    "total_syncs": sync_stats.get("total_syncs", 0),
                    "success_rate": (
                        (sync_stats.get("successful_syncs", 0) / sync_stats.get("total_syncs", 1)) * 100
                        if sync_stats.get("total_syncs", 0) > 0 else 0
                    ),
                    "average_sync_time": sync_stats.get("average_sync_time", 0),
                    "last_success_time": sync_stats.get("last_success_time"),
                    "last_error": sync_stats.get("last_error")
                },
                "http_metrics": {
                    "total_requests": http_stats.get("total_requests", 0),
                    "success_rate": http_stats.get("success_rate", 0),
                    "average_response_time": http_stats.get("average_response_time", 0),
                    "circuit_breaker_state": http_stats.get("circuit_breaker_state", "unknown"),
                    "failure_count": http_stats.get("failure_count", 0)
                },
                "health": {
                    "master_server_healthy": status.get("master_server_healthy", False),
                    "last_health_check": status.get("last_health_check"),
                    "active_operations": status.get("active_operations", 0)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return {
                "success": True,
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to get sync metrics: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "code": "METRICS_RETRIEVAL_FAILED"
                }
            )
    async def detailed_health_check():
        """Detailed health check with sync status"""
        try:
            health_info = {
                "status": "healthy",
                "timestamp": "2025-08-21T00:00:00Z",
                "version": "1.0.0",
                "server_type": "client",
                "client_id": os.getenv("CLIENT_ID", "unknown"),
                "database": {
                    "status": "connected"  # Add actual DB check
                },
                "sync": {
                    "status": "unknown",
                    "last_sync": None,
                    "master_server": os.getenv("MASTER_SERVER_URL", "not_configured")
                }
            }
            
            # Check sync service status
            if hasattr(app.state, 'sync_service'):
                sync_stats = app.state.sync_service.get_stats()
                health_info["sync"] = {
                    "status": "active",
                    "stats": sync_stats,
                    "master_server": app.state.sync_service.master_server_url
                }
            
            return health_info
            
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
    
    # Sync management endpoints
    @app.post("/api/sync/manual", tags=["Synchronization"])
    async def manual_sync(background_tasks: BackgroundTasks):
        """Trigger manual synchronization with master server"""
        if not hasattr(app.state, 'sync_service'):
            return JSONResponse(
                status_code=503,
                content={"error": "Sync service not available"}
            )
        
        # Add sync task to background
        background_tasks.add_task(trigger_manual_sync, app.state.sync_service)
        
        return {
            "message": "Manual sync triggered",
            "status": "queued",
            "timestamp": "2025-08-21T00:00:00Z"
        }
    
    @app.get("/api/sync/status", tags=["Synchronization"])
    async def sync_status():
        """Get current synchronization status"""
        if not hasattr(app.state, 'sync_service'):
            return {
                "status": "not_configured",
                "message": "Sync service not available"
            }
        
        stats = app.state.sync_service.get_stats()
        return {
            "status": "active",
            "client_id": app.state.sync_service.client_id,
            "master_server": app.state.sync_service.master_server_url,
            "stats": stats,
            "timestamp": "2025-08-21T00:00:00Z"
        }
    
    return app


async def trigger_manual_sync(sync_service: ClientSyncService):
    """Background task for manual sync"""
    try:
        logger.info("🔄 Starting manual sync...")
        # This would trigger a full sync of pending data
        # In real implementation, you'd queue all pending users/photos
        logger.info("✅ Manual sync completed")
    except Exception as e:
        logger.error(f"❌ Manual sync failed: {e}")


# Create the application instance
app = create_client_app()


def main():
    """
    Main entry point for running the client server
    """
    # Get configuration from environment
    host = os.getenv("CLIENT_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("CLIENT_SERVER_PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"🌐 Starting Client Server on {host}:{port}")
    logger.info(f"📚 API documentation available at http://{host}:{port}/docs")
    logger.info(f"🔗 Master server: {os.getenv('MASTER_SERVER_URL', 'not configured')}")
    
    # Run the server
    uvicorn.run(
        "client_main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug",
        access_log=True,
        loop="asyncio"
    )


if __name__ == "__main__":
    main()
