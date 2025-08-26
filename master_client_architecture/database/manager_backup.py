"""
Thread-safe database manager for analytics and master server data
"""

import sqlite3
import asyncio
import threading
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from contextlib import asynccontextmanager, contextmanager

class DatabaseManager:
    """
    Thread-safe database manager for analytics and master server data
    
    Features:
    - Connection pooling simulation with locks
    - Atomic operations with proper transaction handling
    - Concurrent read operations support
    - Write operation serialization
    """
    
    def __init__(self, db_path: str = "master_analytics.db"):
        self.db_path = db_path
        
        # Concurrency control
        self._write_lock = threading.Lock()  # Serialize all write operations
        self._connection_lock = threading.Lock()  # Protect connection operations
        
        # Connection management
        self._connection_count = 0
        self._max_connections = 10
        
        # Initialize database
        self.init_database()
    
    @contextmanager
    def _get_connection(self):
        """Thread-safe connection manager"""
        with self._connection_lock:
            if self._connection_count >= self._max_connections:
                raise ConnectionError(f"Maximum connections ({self._max_connections}) exceeded")
            
            self._connection_count += 1
            
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)  # 30 second timeout
            conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and performance
            yield conn
        finally:
            if conn:
                conn.close()
            with self._connection_lock:
                self._connection_count -= 1
    
    @asynccontextmanager
    async def _get_async_connection(self):
        """Async version of connection manager"""
        def get_conn():
            return self._get_connection()
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with await loop.run_in_executor(None, lambda: get_conn()) as conn:
            yield conn
    
    def init_database(self):
        """Initialize master server database tables with proper indexes"""
        with self._write_lock:  # Ensure thread-safe initialization
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # User analytics table (anonymized data only)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_analytics (
                        global_user_id TEXT PRIMARY KEY,
                        age_group TEXT,
                        gender TEXT,
                        client_id TEXT,
                        register_method TEXT,
                        created_at TIMESTAMP,
                        last_active_at TIMESTAMP,
                        FOREIGN KEY (client_id) REFERENCES client_servers(client_id)
                    )
                ''')
                
                # Client servers table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS client_servers (
                        client_id TEXT PRIMARY KEY,
                        client_name TEXT,
                        contact_email TEXT,
                        api_key TEXT UNIQUE,
                        registered_at TIMESTAMP,
                        last_sync TIMESTAMP,
                        status TEXT DEFAULT 'active'
                    )
                ''')
                
                # Sync logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sync_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id TEXT,
                        sync_time TIMESTAMP,
                        records_synced INTEGER,
                        status TEXT,
                        error_message TEXT,
                        operation_id TEXT,
                        FOREIGN KEY (client_id) REFERENCES client_servers(client_id)
                    )
                ''')
                
                # Photo analytics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS photo_analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        global_user_id TEXT,
                        client_id TEXT,
                        image_type TEXT,
                        upload_time TIMESTAMP,
                        hour_of_day INTEGER,
                        day_of_week TEXT,
                        FOREIGN KEY (global_user_id) REFERENCES user_analytics(global_user_id),
                        FOREIGN KEY (client_id) REFERENCES client_servers(client_id)
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_analytics_client_id ON user_analytics(client_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_analytics_created_at ON user_analytics(created_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_logs_client_id ON sync_logs(client_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_logs_sync_time ON sync_logs(sync_time)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_photo_analytics_client_id ON photo_analytics(client_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_photo_analytics_upload_time ON photo_analytics(upload_time)')
                
                conn.commit()
    
    def add_user_analytics(self, user_data: Dict) -> bool:
        """
        Thread-safe addition of user analytics data
        
        Args:
            user_data: Dictionary with user analytics information
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self._write_lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_analytics 
                        (global_user_id, age_group, gender, client_id, register_method, created_at, last_active_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_data["global_user_id"],
                        user_data["age_group"],
                        user_data["gender"],
                        user_data["client_id"],
                        user_data["register_method"],
                        user_data["created_at"],
                        user_data["last_active_at"]
                    ))
                    
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Error adding user analytics: {e}")
                return False
    
    def add_photo_analytics(self, photo_data: Dict) -> bool:
        """
        Thread-safe addition of photo analytics data
        
        Args:
            photo_data: Dictionary with photo analytics information
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self._write_lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO photo_analytics 
                        (global_user_id, client_id, image_type, upload_time, hour_of_day, day_of_week)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        photo_data["global_user_id"],
                        photo_data["client_id"],
                        photo_data["image_type"],
                        photo_data["upload_time"],
                        photo_data["hour_of_day"],
                        photo_data["day_of_week"]
                    ))
                    
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Error adding photo analytics: {e}")
                return False
    
    def log_sync_operation(self, client_id: str, status: str, records_synced: int = 0, 
                          error_message: str = None, operation_id: str = None) -> bool:
        """
        Thread-safe logging of sync operations
        
        Args:
            client_id: Client identifier
            status: Sync status ('success', 'failed', 'in_progress')
            records_synced: Number of records synced
            error_message: Error message if failed
            operation_id: Unique operation identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self._write_lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO sync_logs 
                        (client_id, sync_time, records_synced, status, error_message, operation_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        client_id,
                        datetime.now(),
                        records_synced,
                        status,
                        error_message,
                        operation_id
                    ))
                    
                    conn.commit()
                    return True
            except Exception as e:
                print(f"Error logging sync operation: {e}")
                return False
                client_id TEXT,
                sync_time TIMESTAMP,
                records_synced INTEGER,
                status TEXT,
                error_message TEXT
            )
        ''')
        
        # Photo analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photo_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_user_id TEXT,
                client_id TEXT,
                image_type TEXT,
                upload_time TIMESTAMP,
                hour_of_day INTEGER,
                day_of_week TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_user_growth_data(self, period: str, start_date: date = None, end_date: date = None) -> List[Dict]:
        """Get actual user growth data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if not start_date:
            start_date = date.today() - timedelta(days=90)
        if not end_date:
            end_date = date.today()
        
        if period == "monthly":
            query = '''
                SELECT strftime('%Y-%m', created_at) as period,
                       COUNT(*) as new_users,
                       (SELECT COUNT(*) FROM user_analytics WHERE created_at <= date(ua.created_at, '+1 month', 'start of month', '-1 day')) as total_users
                FROM user_analytics ua
                WHERE date(created_at) BETWEEN ? AND ?
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY period
            '''
        elif period == "weekly":
            query = '''
                SELECT strftime('%Y-W%W', created_at) as period,
                       COUNT(*) as new_users,
                       (SELECT COUNT(*) FROM user_analytics WHERE created_at <= date(ua.created_at, '+7 days')) as total_users
                FROM user_analytics ua
                WHERE date(created_at) BETWEEN ? AND ?
                GROUP BY strftime('%Y-W%W', created_at)
                ORDER BY period
            '''
        else:  # daily
            query = '''
                SELECT date(created_at) as period,
                       COUNT(*) as new_users,
                       (SELECT COUNT(*) FROM user_analytics WHERE created_at <= ua.created_at) as total_users
                FROM user_analytics ua
                WHERE date(created_at) BETWEEN ? AND ?
                GROUP BY date(created_at)
                ORDER BY period
            '''
        
        cursor.execute(query, (start_date, end_date))
        results = cursor.fetchall()
        conn.close()
        
        growth_data = []
        prev_total = 0
        for row in results:
            period_str, new_users, total_users = row
            growth_rate = (new_users / prev_total) if prev_total > 0 else 0
            growth_data.append({
                "period": period_str,
                "new_users": new_users,
                "total_users": total_users,
                "growth_rate": round(growth_rate, 3)
            })
            prev_total = total_users
        
        return growth_data
    
    def get_demographics_data(self, client_id: str = None) -> Dict:
        """Get demographics data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        where_clause = "WHERE client_id = ?" if client_id else ""
        params = [client_id] if client_id else []
        
        # Age groups
        cursor.execute(f'''
            SELECT age_group, COUNT(*) as count
            FROM user_analytics
            {where_clause}
            GROUP BY age_group
        ''', params)
        age_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Genders
        cursor.execute(f'''
            SELECT gender, COUNT(*) as count
            FROM user_analytics
            {where_clause}
            GROUP BY gender
        ''', params)
        gender_data = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total users
        cursor.execute(f'''
            SELECT COUNT(*) FROM user_analytics {where_clause}
        ''', params)
        total_users = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "age_groups": age_data,
            "genders": gender_data,
            "total_users": total_users
        }
    
    def get_client_stats(self, client_id: str) -> Dict:
        """Get statistics for a specific client"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total users for client
        cursor.execute('SELECT COUNT(*) FROM user_analytics WHERE client_id = ?', (client_id,))
        total_users = cursor.fetchone()[0]
        
        # Active users (logged in within last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        cursor.execute('''
            SELECT COUNT(*) FROM user_analytics 
            WHERE client_id = ? AND last_active_at >= ?
        ''', (client_id, thirty_days_ago))
        active_users = cursor.fetchone()[0]
        
        # New users today
        today = date.today()
        cursor.execute('''
            SELECT COUNT(*) FROM user_analytics 
            WHERE client_id = ? AND date(created_at) = ?
        ''', (client_id, today))
        new_users_today = cursor.fetchone()[0]
        
        # New users this month
        month_start = today.replace(day=1)
        cursor.execute('''
            SELECT COUNT(*) FROM user_analytics 
            WHERE client_id = ? AND date(created_at) >= ?
        ''', (client_id, month_start))
        new_users_this_month = cursor.fetchone()[0]
        
        # Client info
        cursor.execute('''
            SELECT client_name, last_sync, status 
            FROM client_servers WHERE client_id = ?
        ''', (client_id,))
        client_info = cursor.fetchone()
        
        conn.close()
        
        return {
            "client_id": client_id,
            "client_name": client_info[0] if client_info else f"Client {client_id}",
            "total_users": total_users,
            "active_users": active_users,
            "new_users_today": new_users_today,
            "new_users_this_month": new_users_this_month,
            "last_sync": client_info[1] if client_info else None,
            "status": client_info[2] if client_info else "unknown"
        }
    
    def get_photo_upload_patterns(self, client_id: str = None) -> Dict:
        """Get photo upload patterns from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        where_clause = "WHERE client_id = ?" if client_id else ""
        params = [client_id] if client_id else []
        
        # Uploads by hour
        cursor.execute(f'''
            SELECT hour_of_day, COUNT(*) as count
            FROM photo_analytics
            {where_clause}
            GROUP BY hour_of_day
            ORDER BY hour_of_day
        ''', params)
        uploads_by_hour = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Uploads by day of week
        cursor.execute(f'''
            SELECT day_of_week, COUNT(*) as count
            FROM photo_analytics
            {where_clause}
            GROUP BY day_of_week
        ''', params)
        uploads_by_day = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Uploads by type
        cursor.execute(f'''
            SELECT image_type, COUNT(*) as count
            FROM photo_analytics
            {where_clause}
            GROUP BY image_type
        ''', params)
        uploads_by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total uploads
        cursor.execute(f'''
            SELECT COUNT(*) FROM photo_analytics {where_clause}
        ''', params)
        total_uploads = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "uploads_by_hour": uploads_by_hour,
            "uploads_by_day": uploads_by_day,
            "uploads_by_type": uploads_by_type,
            "total_uploads": total_uploads
        }
    
    def get_system_health(self) -> Dict:
        """Get system health metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total clients
        cursor.execute('SELECT COUNT(*) FROM client_servers')
        total_clients = cursor.fetchone()[0]
        
        # Active clients
        cursor.execute("SELECT COUNT(*) FROM client_servers WHERE status = 'active'")
        active_clients = cursor.fetchone()[0]
        
        # Total users
        cursor.execute('SELECT COUNT(*) FROM user_analytics')
        total_users = cursor.fetchone()[0]
        
        # Sync issues (failed syncs in last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        cursor.execute('''
            SELECT COUNT(*) FROM sync_logs 
            WHERE status = 'failed' AND sync_time >= ?
        ''', (yesterday,))
        sync_issues = cursor.fetchone()[0]
        
        # Last sync times
        cursor.execute('''
            SELECT client_id, last_sync FROM client_servers 
            WHERE last_sync IS NOT NULL
        ''')
        last_sync_times = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        # Determine system status
        if sync_issues > 10:
            system_status = "critical"
        elif sync_issues > 5 or active_clients < total_clients * 0.8:
            system_status = "warning"
        else:
            system_status = "healthy"
        
        return {
            "total_clients": total_clients,
            "active_clients": active_clients,
            "total_users": total_users,
            "sync_issues": sync_issues,
            "last_sync_times": last_sync_times,
            "system_status": system_status
        }
    
    def store_api_key(self, client_id: str, client_name: str, contact_email: str, api_key: str) -> bool:
        """Store API key for a client"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO client_servers 
                (client_id, client_name, contact_email, api_key, registered_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (client_id, client_name, contact_email, api_key, datetime.now()))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error storing API key: {e}")
            return False
