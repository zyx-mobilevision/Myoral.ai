"""
Client synchronization service for data transfer between client and master servers
Enhanced with robust HTTP client for production-ready API requests
"""

import asyncio
import threading
from typing import Dict, Optional, List, Any
from datetime import datetime
from contextlib import asynccontextmanager
from core.anonymization import DataAnonymizationStrategy
from .robust_http_client import RobustHttpClient, RequestConfig, RetryConfig


class ClientSyncService:
    """
    Production-ready client synchronization service with robust error handling
    
    Features:
    - Robust HTTP client with retry logic and circuit breaker
    - Async locks to prevent concurrent sync operations
    - Atomic operation tracking with detailed error reporting
    - Connection coordination with health monitoring
    - Comprehensive metrics and monitoring
    """
    
    def __init__(self, client_id: str, master_server_url: str, api_key: str):
        self.client_id = client_id
        self.master_server_url = master_server_url
        self.api_key = api_key
        self.anonymizer = DataAnonymizationStrategy()
        
        # Initialize robust HTTP client
        self.http_client = RobustHttpClient(
            base_url=master_server_url,
            api_key=api_key,
            default_timeout=30.0,
            retry_config=RetryConfig(
                max_attempts=3,
                base_delay=2.0,
                max_delay=60.0,
                jitter=True
            ),
            max_connections=20,
            enable_ssl_verification=True
        )
        
        # Concurrency control
        self._sync_lock = asyncio.Lock()
        self._stats_lock = threading.Lock()
        self._operation_count = 0
        self._last_sync_time: Optional[datetime] = None
        self._active_operations = set()
        self._last_health_check: Optional[datetime] = None
        self._master_server_healthy = False
        
        # Enhanced operation tracking
        self.stats = {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "retried_syncs": 0,
            "circuit_breaker_trips": 0,
            "last_error": None,
            "last_success_time": None,
            "average_sync_time": 0.0,
            "master_server_health": "unknown"
        }
    
    @asynccontextmanager
    async def _sync_operation(self, operation_id: str):
        """Context manager for tracking sync operations"""
        async with self._sync_lock:
            if operation_id in self._active_operations:
                raise ValueError(f"Operation {operation_id} already in progress")
            
            self._active_operations.add(operation_id)
            self._operation_count += 1
            
        try:
            yield
        finally:
            async with self._sync_lock:
                self._active_operations.discard(operation_id)  
    
    def _update_stats(self, success: bool, error: str = None, sync_time: float = 0):
        """Thread-safe stats update with enhanced metrics"""
        with self._stats_lock:
            self.stats["total_syncs"] += 1
            if success:
                self.stats["successful_syncs"] += 1
                self.stats["last_success_time"] = datetime.now().isoformat()
                self._last_sync_time = datetime.now()
                
                # Update average sync time
                if self.stats["successful_syncs"] == 1:
                    self.stats["average_sync_time"] = sync_time
                else:
                    current_avg = self.stats["average_sync_time"]
                    total_successful = self.stats["successful_syncs"]
                    self.stats["average_sync_time"] = (
                        (current_avg * (total_successful - 1) + sync_time) / total_successful
                    )
            else:
                self.stats["failed_syncs"] += 1
                self.stats["last_error"] = error
                
            # Update HTTP client stats
            http_stats = self.http_client.get_stats()
            self.stats["retried_syncs"] = http_stats.get("retried_requests", 0)
            self.stats["circuit_breaker_trips"] = http_stats.get("circuit_breaker_trips", 0)
    
    async def check_master_server_health(self) -> bool:
        """
        Check master server health and update internal status
        
        Returns:
            bool: True if master server is healthy, False otherwise
        """
        try:
            health_result = await self.http_client.health_check()
            self._master_server_healthy = health_result.get('healthy', False)
            self._last_health_check = datetime.now()
            
            with self._stats_lock:
                if self._master_server_healthy:
                    self.stats["master_server_health"] = "healthy"
                else:
                    self.stats["master_server_health"] = f"unhealthy: {health_result.get('error', 'unknown')}"
                    
            return self._master_server_healthy
            
        except Exception as e:
            self._master_server_healthy = False
            self._last_health_check = datetime.now()
            
            with self._stats_lock:
                self.stats["master_server_health"] = f"error: {str(e)}"
                
            return False
    
    async def sync_user_data(self, user_data: Dict) -> Dict[str, any]:
        """
        Production-ready sync of anonymized user data to master server
        
        Args:
            user_data: User data dictionary with keys: userId, birthdate, gender, etc.
            
        Returns:
            Dict: Sync result with success status, timing, and error details
        """
        operation_id = f"user_sync_{user_data.get('userId', 'unknown')}_{datetime.now().timestamp()}"
        start_time = datetime.now()
        
        try:
            async with self._sync_operation(operation_id):
                # Check master server health first
                if not await self.check_master_server_health():
                    raise Exception("Master server is not healthy")
                
                # Anonymize the data
                anonymized_data = {
                    "global_user_id": self.anonymizer.design_user_id_anonymization(
                        user_data["userId"], self.client_id
                    ),
                    "age_group": self.anonymizer.design_age_anonymization(user_data["birthdate"]),
                    "gender": user_data.get("gender", "unknown"),
                    "client_id": self.client_id,
                    "register_method": user_data.get("register_method", "email"),
                    "created_at": user_data["createdAt"],
                    "last_active_at": user_data.get("lastUpdatedAt", user_data["createdAt"]),
                    "sync_timestamp": datetime.now().isoformat(),
                    "operation_id": operation_id
                }
                
                # Send to master server using robust HTTP client
                config = RequestConfig(
                    timeout=30.0,
                    headers={"X-Operation-Type": "user-sync", "X-Client-ID": self.client_id}
                )
                
                result = await self.http_client.post(
                    "/api/analytics/users", 
                    data=anonymized_data,
                    config=config
                )
                
                sync_time = (datetime.now() - start_time).total_seconds()
                
                if result.get('success', False):
                    self._update_stats(success=True, sync_time=sync_time)
                    return {
                        "success": True,
                        "operation_id": operation_id,
                        "sync_time": sync_time,
                        "response": result.get('data', {}),
                        "request_id": result.get('request_id')
                    }
                else:
                    error_msg = result.get('error', 'Unknown error')
                    self._update_stats(success=False, error=error_msg, sync_time=sync_time)
                    return {
                        "success": False,
                        "operation_id": operation_id,
                        "error": error_msg,
                        "sync_time": sync_time,
                        "attempts": result.get('attempts', 1)
                    }
                
        except ValueError as e:
            # Operation already in progress
            return {
                "success": False,
                "operation_id": operation_id,
                "error": f"Duplicate sync operation prevented: {e}",
                "sync_time": 0
            }
        except Exception as e:
            sync_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"User sync error: {e}"
            self._update_stats(success=False, error=error_msg, sync_time=sync_time)
            return {
                "success": False,
                "operation_id": operation_id,
                "error": error_msg,
                "sync_time": sync_time
            }

    async def sync_photo_analytics(self, photo_data: Dict) -> Dict[str, any]:
        """
        Production-ready sync of photo analytics (no image data) to master server
        
        Args:
            photo_data: Photo metadata with keys: user_id, timestamp, image_type
            
        Returns:
            Dict: Sync result with success status, timing, and error details
        """
        operation_id = f"photo_sync_{photo_data.get('user_id', 'unknown')}_{datetime.now().timestamp()}"
        start_time = datetime.now()
        
        try:
            async with self._sync_operation(operation_id):
                # Check master server health first
                if not await self.check_master_server_health():
                    raise Exception("Master server is not healthy")
                
                upload_time = datetime.fromisoformat(photo_data["timestamp"])
                anonymized_data = {
                    "global_user_id": self.anonymizer.design_user_id_anonymization(
                        photo_data["user_id"], self.client_id
                    ),
                    "client_id": self.client_id,
                    "image_type": photo_data["image_type"],
                    "upload_time": photo_data["timestamp"],
                    "hour_of_day": upload_time.hour,
                    "day_of_week": upload_time.strftime("%A"),
                    "sync_timestamp": datetime.now().isoformat(),
                    "operation_id": operation_id
                }
                
                # Send to master server using robust HTTP client
                config = RequestConfig(
                    timeout=30.0,
                    headers={"X-Operation-Type": "photo-sync", "X-Client-ID": self.client_id}
                )
                
                result = await self.http_client.post(
                    "/api/analytics/photos",
                    data=anonymized_data,
                    config=config
                )
                
                sync_time = (datetime.now() - start_time).total_seconds()
                
                if result.get('success', False):
                    self._update_stats(success=True, sync_time=sync_time)
                    return {
                        "success": True,
                        "operation_id": operation_id,
                        "sync_time": sync_time,
                        "response": result.get('data', {}),
                        "request_id": result.get('request_id')
                    }
                else:
                    error_msg = result.get('error', 'Unknown error')
                    self._update_stats(success=False, error=error_msg, sync_time=sync_time)
                    return {
                        "success": False,
                        "operation_id": operation_id,
                        "error": error_msg,
                        "sync_time": sync_time,
                        "attempts": result.get('attempts', 1)
                    }
                
        except ValueError as e:
            # Operation already in progress
            return {
                "success": False,
                "operation_id": operation_id,
                "error": f"Duplicate photo sync operation prevented: {e}",
                "sync_time": 0
            }
        except Exception as e:
            sync_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Photo sync error: {e}"
            self._update_stats(success=False, error=error_msg, sync_time=sync_time)
            return {
                "success": False,
                "operation_id": operation_id,
                "error": error_msg,
                "sync_time": sync_time
            }
    
    async def get_sync_status(self) -> Dict:
        """Get comprehensive sync service status and statistics"""
        async with self._sync_lock:
            active_ops = len(self._active_operations)
            operation_count = self._operation_count
            
        with self._stats_lock:
            stats_copy = self.stats.copy()
            last_sync = self._last_sync_time
            
        # Get HTTP client statistics
        http_stats = self.http_client.get_stats()
        
        return {
            "client_id": self.client_id,
            "active_operations": active_ops,
            "total_operations": operation_count,
            "last_sync_time": last_sync.isoformat() if last_sync else None,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "master_server_healthy": self._master_server_healthy,
            "master_server_url": self.master_server_url,
            "sync_statistics": stats_copy,
            "http_client_stats": {
                "total_requests": http_stats.get("total_requests", 0),
                "success_rate": http_stats.get("success_rate", 0),
                "average_response_time": http_stats.get("average_response_time", 0),
                "circuit_breaker_state": http_stats.get("circuit_breaker_state", "unknown"),
                "failure_count": http_stats.get("failure_count", 0),
                "last_failure_time": http_stats.get("last_failure_time")
            }
        }
    
    async def bulk_sync_operation(self, operations: List[Dict]) -> Dict[str, Any]:
        """
        Perform bulk sync operations with batching and error handling
        
        Args:
            operations: List of sync operations, each with 'type' and 'data' keys
            
        Returns:
            Dict: Bulk sync results with individual operation status
        """
        if not operations:
            return {"success": True, "total": 0, "successful": 0, "failed": 0, "results": []}
        
        operation_id = f"bulk_sync_{datetime.now().timestamp()}"
        start_time = datetime.now()
        results = []
        successful_count = 0
        failed_count = 0
        
        try:
            # Check master server health before bulk operation
            if not await self.check_master_server_health():
                raise Exception("Master server is not healthy - aborting bulk sync")
            
            # Process operations in batches to avoid overwhelming the server
            batch_size = 10
            for i in range(0, len(operations), batch_size):
                batch = operations[i:i + batch_size]
                batch_results = []
                
                # Process batch concurrently but with limited concurrency
                semaphore = asyncio.Semaphore(5)  # Max 5 concurrent operations
                
                async def process_operation(op):
                    async with semaphore:
                        if op.get('type') == 'user':
                            return await self.sync_user_data(op['data'])
                        elif op.get('type') == 'photo':
                            return await self.sync_photo_analytics(op['data'])
                        else:
                            return {
                                "success": False,
                                "error": f"Unknown operation type: {op.get('type')}"
                            }
                
                batch_tasks = [process_operation(op) for op in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process batch results
                for result in batch_results:
                    if isinstance(result, Exception):
                        result = {
                            "success": False,
                            "error": f"Exception: {str(result)}"
                        }
                    
                    results.append(result)
                    if result.get('success', False):
                        successful_count += 1
                    else:
                        failed_count += 1
                
                # Add delay between batches to be respectful to the server
                if i + batch_size < len(operations):
                    await asyncio.sleep(0.5)
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "operation_id": operation_id,
                "total": len(operations),
                "successful": successful_count,
                "failed": failed_count,
                "sync_time": total_time,
                "results": results
            }
            
        except Exception as e:
            total_time = (datetime.now() - start_time).total_seconds()
            return {
                "success": False,
                "operation_id": operation_id,
                "error": str(e),
                "total": len(operations),
                "successful": successful_count,
                "failed": failed_count,
                "sync_time": total_time,
                "results": results
            }
    
    async def reset_circuit_breaker(self) -> Dict[str, any]:
        """
        Manually reset the circuit breaker and perform health check
        
        Returns:
            Dict: Reset result and current health status
        """
        try:
            await self.http_client.reset_circuit_breaker()
            health_check = await self.check_master_server_health()
            
            return {
                "success": True,
                "circuit_breaker_reset": True,
                "health_check_passed": health_check,
                "message": "Circuit breaker reset successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to reset circuit breaker"
            }
    
    async def close(self):
        """Close HTTP client and cleanup resources"""
        if hasattr(self, 'http_client'):
            await self.http_client.close()
    
    async def _send_to_master(self, endpoint: str, data: Dict) -> bool:
        """
        Send data to master server (placeholder for actual HTTP implementation)
        
        In Phase 2, this would implement:
        - HTTP client with connection pooling
        - Retry logic with exponential backoff
        - Authentication headers
        - Response validation
        """
        # Placeholder for actual HTTP implementation
        # import aiohttp
        # async with aiohttp.ClientSession() as session:
        #     headers = {"Authorization": f"Bearer {self.api_key}"}
        #     async with session.post(f"{self.master_server_url}{endpoint}", 
        #                           json=data, headers=headers) as response:
        #         return response.status == 200
        return True
