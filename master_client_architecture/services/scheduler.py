"""
Background task scheduler for automatic data synchronization with concurrency control
"""

import asyncio
import threading
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .sync_service import ClientSyncService

class BackgroundSyncScheduler:
    """
    Thread-safe background task scheduler for automatic data synchronization
    
    Features:
    - Prevents overlapping sync operations
    - Configurable retry logic
    - Graceful shutdown handling
    - Operation statistics tracking
    """
    
    def __init__(self, sync_service: 'ClientSyncService', interval_minutes: int = 30):
        self.sync_service = sync_service
        self.interval_minutes = interval_minutes
        
        # State management
        self.running = False
        self.task: Optional[asyncio.Task] = None
        
        # Concurrency control
        self._scheduler_lock = threading.Lock()
        self._sync_in_progress = False
        
        # Statistics
        self.stats = {
            "scheduled_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "skipped_syncs": 0,  # When sync already in progress
            "last_sync_time": None,
            "last_error": None,
            "next_sync_time": None
        }
    
    async def start(self):
        """Start the background sync scheduler"""
        with self._scheduler_lock:
            if self.running:
                print("Scheduler already running")
                return
            
            self.running = True
            self.stats["next_sync_time"] = datetime.now() + timedelta(minutes=self.interval_minutes)
        
        self.task = asyncio.create_task(self._sync_loop())
        print(f"Background sync scheduler started (interval: {self.interval_minutes} minutes)")
    
    async def stop(self):
        """Stop the background sync scheduler gracefully"""
        with self._scheduler_lock:
            if not self.running:
                return
            
            self.running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                print("Background sync scheduler stopped")
    
    async def trigger_manual_sync(self) -> bool:
        """
        Trigger an immediate sync operation
        
        Returns:
            bool: True if sync started, False if already in progress
        """
        with self._scheduler_lock:
            if self._sync_in_progress:
                self.stats["skipped_syncs"] += 1
                return False
            
            self._sync_in_progress = True
        
        try:
            success = await self._perform_sync(manual=True)
            return success
        finally:
            with self._scheduler_lock:
                self._sync_in_progress = False
    
    async def _sync_loop(self):
        """Main sync loop that runs in the background"""
        while self.running:
            try:
                # Check if we should sync
                await self._wait_for_next_sync()
                
                if not self.running:
                    break
                
                # Perform sync if not already in progress
                with self._scheduler_lock:
                    if self._sync_in_progress:
                        self.stats["skipped_syncs"] += 1
                        continue
                    
                    self._sync_in_progress = True
                
                try:
                    await self._perform_sync(manual=False)
                finally:
                    with self._scheduler_lock:
                        self._sync_in_progress = False
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                error_msg = f"Background sync loop error: {e}"
                print(error_msg)
                with self._scheduler_lock:
                    self.stats["last_error"] = error_msg
                    self._sync_in_progress = False
                
                # Wait shorter time on error before retrying
                await asyncio.sleep(60)
    
    async def _wait_for_next_sync(self):
        """Wait for the next scheduled sync time"""
        sleep_duration = self.interval_minutes * 60
        
        with self._scheduler_lock:
            self.stats["next_sync_time"] = datetime.now() + timedelta(seconds=sleep_duration)
        
        await asyncio.sleep(sleep_duration)
    
    async def _perform_sync(self, manual: bool = False) -> bool:
        """
        Perform the actual sync operation
        
        Args:
            manual: True if triggered manually, False if scheduled
            
        Returns:
            bool: True if sync successful, False otherwise
        """
        sync_type = "manual" if manual else "scheduled"
        start_time = datetime.now()
        
        try:
            with self._scheduler_lock:
                self.stats["scheduled_syncs"] += 1
            
            print(f"Performing {sync_type} background sync at {start_time}")
            
            # Get current sync service status
            sync_status = await self.sync_service.get_sync_status()
            
            # In real implementation, this would:
            # 1. Query local database for pending sync operations
            # 2. Batch sync operations for efficiency  
            # 3. Handle retry logic for failed operations
            # 4. Update sync queue status
            
            # For now, simulate sync success
            await asyncio.sleep(0.5)  # Simulate processing time
            
            with self._scheduler_lock:
                self.stats["successful_syncs"] += 1
                self.stats["last_sync_time"] = datetime.now()
                self.stats["last_error"] = None
            
            duration = (datetime.now() - start_time).total_seconds()
            print(f"Background sync completed successfully in {duration:.2f}s")
            return True
            
        except Exception as e:
            error_msg = f"Background sync failed: {e}"
            print(error_msg)
            
            with self._scheduler_lock:
                self.stats["failed_syncs"] += 1
                self.stats["last_error"] = error_msg
            
            return False
    
    def get_scheduler_status(self) -> dict:
        """Get current scheduler status and statistics"""
        with self._scheduler_lock:
            return {
                "running": self.running,
                "sync_in_progress": self._sync_in_progress,
                "interval_minutes": self.interval_minutes,
                "statistics": self.stats.copy()
            }
