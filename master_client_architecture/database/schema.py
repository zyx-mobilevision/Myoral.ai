"""
Database schema planning and migration utilities
"""

class DatabaseSchemaPlanning:
    """Plan database schema changes for both servers"""
    
    def plan_master_server_schema(self):
        """Design master server database tables for analytics and monitoring"""
        return {
            "user_analytics": ["global_user_id (PK)", "age_group", "gender", "client_id", "register_method", "created_at", "last_active_at"],
            "client_servers": ["client_id (PK)", "client_name", "contact_email", "api_key", "registered_at", "last_sync", "status"],
            "sync_logs": ["id (PK)", "client_id", "sync_time", "records_synced", "status", "error_message"],
            "photo_analytics": ["id (PK)", "global_user_id", "client_id", "image_type", "upload_time", "hour_of_day", "day_of_week"]
        }

    def plan_client_server_modifications(self):
        """Plan changes to client server database for sync and analytics"""
        return {
            "User_table_additions": ["last_synced_at", "sync_status", "global_user_id"],
            "new_tables": [
                {
                    "sync_queue": ["id (PK)", "record_type", "record_id", "status", "error_message", "created_at", "updated_at"]
                },
                {
                    "sync_errors": ["id (PK)", "record_type", "record_id", "error_message", "timestamp"]
                }
            ]
        }
