"""
Application factory functions for creating FastAPI instances

This module provides factory functions to create master and client server applications
with proper configuration and dependency injection.
"""

from fastapi import FastAPI
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def create_master_server_app() -> FastAPI:
    """
    Create and configure the master server FastAPI application
    
    Returns:
        FastAPI: Configured master server application
    """
    try:
        # Try to import from master_main if available
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "master_main", 
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "master_main.py")
        )
        if spec and spec.loader:
            master_main = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(master_main)
            return master_main.create_master_app()
    except Exception:
        pass
    
    # Fallback to API design
    try:
        from ..api import MasterServerAPIDesign
        master_api = MasterServerAPIDesign()
        return master_api.get_app()
    except ImportError:
        # Basic fallback
        app = FastAPI(title="MyOral Master Server", version="1.0.0")
        
        @app.get("/")
        async def root():
            return {"message": "MyOral Master Server", "version": "1.0.0"}
        
        return app


def create_client_server_app(client_id: str = "default_client") -> FastAPI:
    """
    Create and configure a client server application
    
    Args:
        client_id: Unique identifier for this client instance
        
    Returns:
        FastAPI: Configured client server application
    """
    try:
        # Try to import from client_main if available
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "client_main", 
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "client_main.py")
        )
        if spec and spec.loader:
            client_main = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(client_main)
            return client_main.create_client_app()
    except Exception:
        pass
    
    # Fallback to API design
    try:
        from ..api import ClientServerAPIDesign
        client_api = ClientServerAPIDesign(client_id)
        return client_api.get_app()
    except ImportError:
        # Basic fallback
        app = FastAPI(title="MyOral Client Server", version="1.0.0")
        
        @app.get("/")
        async def root():
            return {"message": f"MyOral Client Server - {client_id}", "version": "1.0.0"}
        
        return app


# Export the factory functions
__all__ = ["create_master_server_app", "create_client_server_app"]
