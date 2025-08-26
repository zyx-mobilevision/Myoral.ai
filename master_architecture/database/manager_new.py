"""
Thread-safe database manager for analytics and master server data
"""

import sqlite3
import threading
from datetime import datetime, date, timedelta
from typing import Dict, List
from contextlib import contextmanager

class DatabaseManager:
    """
    Thread-safe database manager for analytics and master server data
    
    Features:
    - Connection management with locks
    - Atomic operations with proper transaction handling
    - Write operation serialization
    - Performance optimizations with indexes
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
                        last_active_at TIMESTAMP
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
                        operation_id TEXT
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
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_analytics_client_id ON user_analytics(client_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_analytics_created_at ON user_analytics(created_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_logs_client_id ON sync_logs(client_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_logs_sync_time ON sync_logs(sync_time)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_photo_analytics_client_id ON photo_analytics(client_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_photo_analytics_upload_time ON photo_analytics(upload_time)')
                
                conn.commit()
    
    def add_user_analytics(self, user_data: Dict) -> bool:
        """Thread-safe addition of user analytics data"""
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
    
    def get_user_growth_data(self, period: str, start_date: date = None, end_date: date = None) -> List[Dict]:
        """Get user growth data from database (read-only, allows concurrent access)"""
        # Read operations don't need write lock, multiple concurrent reads are safe
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if not start_date:
                start_date = date.today() - timedelta(days=90)
            if not end_date:
                end_date = date.today()
            
            if period == "monthly":
                query = '''
                    SELECT strftime('%Y-%m', created_at) as period,
                           COUNT(*) as new_users
                    FROM user_analytics
                    WHERE date(created_at) BETWEEN ? AND ?
                    GROUP BY strftime('%Y-%m', created_at)
                    ORDER BY period
                '''
            elif period == "weekly":
                query = '''
                    SELECT strftime('%Y-W%W', created_at) as period,
                           COUNT(*) as new_users
                    FROM user_analytics
                    WHERE date(created_at) BETWEEN ? AND ?
                    GROUP BY strftime('%Y-W%W', created_at)
                    ORDER BY period
                '''
            else:  # daily
                query = '''
                    SELECT date(created_at) as period,
                           COUNT(*) as new_users
                    FROM user_analytics
                    WHERE date(created_at) BETWEEN ? AND ?
                    GROUP BY date(created_at)
                    ORDER BY period
                '''
            
            cursor.execute(query, (start_date, end_date))
            results = cursor.fetchall()
            
            growth_data = []
            for row in results:
                period_str, new_users = row
                growth_data.append({
                    "period": period_str,
                    "new_users": new_users,
                    "total_users": new_users,  # Simplified for now
                    "growth_rate": 0.0
                })
            
            return growth_data
    
    def get_demographics_data(self, client_id: str = None) -> Dict:
        """Get demographics data from database"""
        with self._get_connection() as conn:
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
            
            return {
                "age_groups": age_data,
                "genders": gender_data,
                "total_users": total_users
            }
    
    def log_sync_operation(self, client_id: str, status: str, records_synced: int = 0, 
                          error_message: str = None, operation_id: str = None) -> bool:
        """Thread-safe logging of sync operations"""
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
    
    def get_system_health(self) -> Dict:
        """Get system health metrics"""
        with self._get_connection() as conn:
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
    
    def get_connection_status(self) -> Dict:
        """Get database connection status for monitoring"""
        with self._connection_lock:
            return {
                "active_connections": self._connection_count,
                "max_connections": self._max_connections,
                "connection_utilization": self._connection_count / self._max_connections
            }
