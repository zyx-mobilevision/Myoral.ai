"""
Thread-safe client server API implementation with sync management endpoints
"""

import hashlib
import asyncio
import threading
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, status

from master_architecture.services import ClientSyncService

class ClientServerAPIDesign:
    """
    Thread-safe client server sync management endpoints
    
    Features:
    - Atomic state operations
    - Concurrent request handling
    - Duplicate operation prevention
    - Statistics tracking
    """
    
    def __init__(self, client_id: str = "default_client"):
        self.app = FastAPI(
            title="MyOral Client Server Sync API",
            description="Thread-safe endpoints for client-to-master sync management",
            version="1.0.0"
        )
        self.client_id = client_id
        self.sync_service: Optional[ClientSyncService] = None
        
        # Thread-safe state management
        self._state_lock = threading.Lock()
        self._operation_lock = asyncio.Lock()
        
        self.sync_state = {
            "last_sync": None,
            "pending": 0,
            "failed": 0,
            "synced_records": 0,
            "api_key": None,
            "master_server_url": None,
            "configuration_time": None
        }
        
        self._setup_routes()
    
    def _atomic_state_update(self, updates: dict):
        """Thread-safe atomic state updates"""
        with self._state_lock:
            for key, value in updates.items():
                if callable(value):
                    # Support for increment/decrement operations
                    self.sync_state[key] = value(self.sync_state.get(key, 0))
                else:
                    self.sync_state[key] = value
    
    def _get_state_copy(self) -> dict:
        """Get thread-safe copy of current state"""
        with self._state_lock:
            return self.sync_state.copy()

    
    def _setup_routes(self):
        @self.app.post("/api/sync/configure", tags=["Sync"])
        async def configure_sync(master_url: str, api_key: str):
            """Configure sync settings with master server (thread-safe)"""
            async with self._operation_lock:  # Prevent concurrent configuration
                self._atomic_state_update({
                    "master_server_url": master_url,
                    "api_key": api_key,
                    "configuration_time": datetime.now().isoformat()
                })
                
                self.sync_service = ClientSyncService(self.client_id, master_url, api_key)
                
            return {"status": "configured", "master_url": master_url, "client_id": self.client_id}

        @self.app.post("/api/sync/manual-sync", tags=["Sync"])
        async def manual_sync():
            """Trigger manual sync of all pending data to master server (thread-safe)"""
            if not self.sync_service:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sync not configured. Call /api/sync/configure first."
                )
            
            async with self._operation_lock:  # Prevent concurrent manual syncs
                # Get current state
                state = self._get_state_copy()
                
                # Simulate sync processing
                synced = state["pending"]
                
                # Atomic state update
                self._atomic_state_update({
                    "synced_records": lambda x: x + synced,
                    "pending": 0,
                    "failed": 0,
                    "last_sync": datetime.now().isoformat()
                })
                
            return {
                "status": "completed", 
                "synced_records": synced, 
                "last_sync": self._get_state_copy()["last_sync"]
            }

        @self.app.get("/api/sync/status", tags=["Sync"])
        async def sync_status():
            """Get current sync status (thread-safe read)"""
            state = self._get_state_copy()
            
            # Add sync service status if available
            sync_service_status = None
            if self.sync_service:
                sync_service_status = await self.sync_service.get_sync_status()
            
            return {
                "client_state": state,
                "sync_service_status": sync_service_status,
                "configured": self.sync_service is not None
            }

        @self.app.post("/api/sync/register-with-master", tags=["Sync"])
        async def register_with_master(client_name: str, contact_email: str, master_url: str):
            """Register this client server with the master server (thread-safe)"""
            if not master_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Master server URL required"
                )
            
            async with self._operation_lock:  # Atomic registration
                # Generate API key
                api_key = hashlib.sha256(
                    f"{self.client_id}:{client_name}:{datetime.now()}".encode()
                ).hexdigest()
                
                # Update state atomically
                self._atomic_state_update({
                    "api_key": api_key,
                    "master_server_url": master_url,
                    "configuration_time": datetime.now().isoformat()
                })
                
                self.sync_service = ClientSyncService(self.client_id, master_url, api_key)
            
            return {
                "api_key": api_key, 
                "client_id": self.client_id, 
                "status": "registered",
                "client_name": client_name
            }

        @self.app.post("/api/sync/queue", tags=["Sync"])
        async def queue_sync_item(count: int = 1, fail: bool = False):
            """Add items to sync queue (thread-safe simulation)"""
            if fail:
                self._atomic_state_update({"failed": lambda x: x + count})
            else:
                self._atomic_state_update({"pending": lambda x: x + count})
                
            state = self._get_state_copy()
            return {"pending": state["pending"], "failed": state["failed"]}
        
        @self.app.get("/api/sync/health", tags=["Sync"])
        async def sync_health():
            """Get sync system health status"""
            state = self._get_state_copy()
            
            # Determine health status
            if state["failed"] > 10:
                health_status = "critical"
            elif state["failed"] > 5:
                health_status = "warning"
            else:
                health_status = "healthy"
            
            return {
                "status": health_status,
                "sync_configured": self.sync_service is not None,
                "pending_operations": state["pending"],
                "failed_operations": state["failed"],
                "last_sync": state["last_sync"],
                "uptime": "operational"
            }

    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance"""
        return self.app
    
    async def get_detailed_status(self) -> dict:
        """Get comprehensive status information for monitoring"""
        state = self._get_state_copy()
        
        sync_service_status = None
        if self.sync_service:
            sync_service_status = await self.sync_service.get_sync_status()
        
        return {
            "client_id": self.client_id,
            "configuration": {
                "configured": self.sync_service is not None,
                "master_url": state.get("master_server_url"),
                "configuration_time": state.get("configuration_time")
            },
            "operations": {
                "pending": state["pending"],
                "failed": state["failed"],
                "synced_records": state["synced_records"],
                "last_sync": state["last_sync"]
            },
            "sync_service": sync_service_status
        }