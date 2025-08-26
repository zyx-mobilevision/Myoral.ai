"""
Environment Setup Utility for Master-Client Architecture

This module provides utilities for setting up the development environment,
database instances, and project structure for the MyOral master-client architecture.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List
import psycopg2
from psycopg2 import sql
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnvironmentSetup:
    """
    Set up development environment for master-client architecture
    
    Handles:
    - Database instance creation
    - Environment variable configuration
    - Project structure organization
    - Initial setup validation
    """
    
    def __init__(self, base_path: str = None):
        """Initialize environment setup with base project path"""
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent.parent
        self.env_file_path = self.base_path / ".env"
        
    def setup_database_instances(self, 
                                admin_user: str = "postgres", 
                                admin_password: str = None,
                                host: str = "localhost",
                                port: int = 5432) -> bool:
        """
        Create separate PostgreSQL databases for master and client servers
        
        Args:
            admin_user: PostgreSQL admin user (default: postgres)
            admin_password: PostgreSQL admin password
            host: Database host (default: localhost)
            port: Database port (default: 5432)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not admin_password:
            admin_password = input("Enter PostgreSQL admin password: ")
            
        databases_to_create = [
            {
                "name": "oral_db_client",
                "description": "Client server database (existing data)"
            },
            {
                "name": "oral_db_master", 
                "description": "Master server database (analytics only)"
            }
        ]
        
        try:
            # Connect to PostgreSQL as admin
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=admin_user,
                password=admin_password,
                database="postgres"  # Connect to default database
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            for db_config in databases_to_create:
                db_name = db_config["name"]
                description = db_config["description"]
                
                # Check if database exists
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (db_name,)
                )
                
                if cursor.fetchone():
                    logger.info(f"Database '{db_name}' already exists")
                else:
                    # Create database
                    cursor.execute(
                        sql.SQL("CREATE DATABASE {}").format(
                            sql.Identifier(db_name)
                        )
                    )
                    logger.info(f"Created database '{db_name}' - {description}")
                    
            cursor.close()
            conn.close()
            
            logger.info("✅ Database setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            return False
    
    def setup_environment_variables(self, 
                                  db_user: str = "zyxczh",
                                  db_password: str = "114514",
                                  db_host: str = "localhost",
                                  db_port: int = 5432) -> bool:
        """
        Create or update .env file with master-client configuration
        
        Args:
            db_user: Database username
            db_password: Database password  
            db_host: Database host
            db_port: Database port
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            env_content = f"""# =============================================================================
# MyOral Master-Client Architecture Environment Configuration
# =============================================================================

# Client Server Database (existing application)
CLIENT_DB_USER={db_user}
CLIENT_DB_PASS={db_password}
CLIENT_DB_HOST={db_host}
CLIENT_DB_PORT={db_port}
CLIENT_DB_NAME=oral_db_client

# Master Server Database (analytics only)
MASTER_DB_USER={db_user}
MASTER_DB_PASS={db_password}
MASTER_DB_HOST={db_host}
MASTER_DB_PORT={db_port}
MASTER_DB_NAME=oral_db_master

# Master Server Configuration
MASTER_SERVER_SALT=myoral_secure_salt_2025_v1
CLIENT_ID=client_001
MASTER_SERVER_URL=http://localhost:8001
MASTER_SERVER_PORT=8001

# Client Server Configuration
CLIENT_SERVER_PORT=8000

# Security Configuration
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# MQTT Configuration (for real-time sync)
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_pass
MQTT_TOPIC_PREFIX=myoral

# Email Configuration (existing)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASS=your-app-password

# Development/Production Environment
ENVIRONMENT=development
DEBUG=true

# API Security
API_KEY_EXPIRY_DAYS=90
MAX_API_REQUESTS_PER_MINUTE=100

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=myoral_app.log
"""
            
            # Backup existing .env file if it exists
            if self.env_file_path.exists():
                backup_path = self.env_file_path.with_suffix('.env.backup')
                shutil.copy2(self.env_file_path, backup_path)
                logger.info(f"Backed up existing .env to {backup_path}")
            
            # Write new .env file
            with open(self.env_file_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
                
            logger.info(f"✅ Environment variables configured in {self.env_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Environment setup failed: {e}")
            return False
    
    def create_project_structure(self) -> bool:
        """
        Create organized folder structure for master-client architecture
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Define the target project structure
            structure = {
                "client_server": {
                    "description": "Client server application (existing code)",
                    "folders": ["routers", "utils", "tests"],
                    "files": ["main.py", "database.py", "requirements.txt"]
                },
                "master_server": {
                    "description": "Master server for analytics",
                    "folders": ["analytics", "utils", "tests"],
                    "files": ["main.py", "database.py", "requirements.txt"]
                },
                "shared": {
                    "description": "Shared utilities and common code",
                    "folders": ["utils", "models", "security"],
                    "files": ["__init__.py"]
                },
                "scripts": {
                    "description": "Setup and maintenance scripts",
                    "folders": [],
                    "files": ["setup_databases.py", "migrate_data.py"]
                },
                "config": {
                    "description": "Configuration files",
                    "folders": [],
                    "files": ["logging.conf", "nginx.conf.template"]
                },
                "docs": {
                    "description": "Documentation",
                    "folders": ["api", "setup"],
                    "files": ["README.md", "DEPLOYMENT.md"]
                }
            }
            
            # Create the directory structure
            for main_folder, config in structure.items():
                main_path = self.base_path / main_folder
                main_path.mkdir(exist_ok=True)
                
                # Create subfolders
                for subfolder in config["folders"]:
                    subfolder_path = main_path / subfolder
                    subfolder_path.mkdir(exist_ok=True)
                    
                    # Create __init__.py in Python packages
                    init_file = subfolder_path / "__init__.py"
                    if not init_file.exists():
                        init_file.touch()
                
                # Create placeholder files
                for filename in config["files"]:
                    file_path = main_path / filename
                    if not file_path.exists():
                        if filename.endswith('.py'):
                            with open(file_path, 'w') as f:
                                f.write(f'"""{config["description"]}"""\n\n# TODO: Implement\n')
                        elif filename == "README.md":
                            with open(file_path, 'w') as f:
                                f.write(f"# {main_folder.replace('_', ' ').title()}\n\n{config['description']}\n")
                        else:
                            file_path.touch()
                
                logger.info(f"Created structure for {main_folder}")
            
            # Create main project README
            main_readme = self.base_path / "README_PROJECT_STRUCTURE.md"
            if not main_readme.exists():
                readme_content = """# MyOral Master-Client Architecture

## Project Structure

```
myoral_backend/
├── client_server/          # Client server application (existing code)
│   ├── routers/           # API endpoints for client operations
│   ├── utils/             # Client-specific utilities  
│   ├── tests/             # Client server tests
│   ├── main.py            # Client server FastAPI app
│   ├── database.py        # Client database models and operations
│   └── requirements.txt   # Client dependencies
├── master_server/          # Master server for analytics
│   ├── analytics/         # Analytics endpoints and logic
│   ├── utils/             # Master server utilities
│   ├── tests/             # Master server tests  
│   ├── main.py            # Master server FastAPI app
│   ├── database.py        # Master database models and operations
│   └── requirements.txt   # Master dependencies
├── shared/                 # Shared utilities and common code
│   ├── utils/             # Common utilities
│   ├── models/            # Shared data models
│   ├── security/          # Security utilities
│   └── __init__.py
├── scripts/                # Setup and maintenance scripts
│   ├── setup_databases.py # Database initialization
│   └── migrate_data.py    # Data migration utilities
├── config/                 # Configuration files
│   ├── logging.conf       # Logging configuration
│   └── nginx.conf.template # Nginx configuration template
└── docs/                   # Documentation
    ├── api/               # API documentation
    ├── setup/             # Setup guides
    ├── README.md          # Main documentation
    └── DEPLOYMENT.md      # Deployment guide
```

## Setup Instructions

1. Run environment setup: `python utils/environment_setup.py`
2. Configure databases: `python scripts/setup_databases.py`
3. Start client server: `uvicorn client_server.main:app --port 8000`
4. Start master server: `uvicorn master_server.main:app --port 8001`

## Security Notes

- Client server handles PII and medical data
- Master server only stores anonymized analytics data
- All communication secured with HTTPS
- API keys required for master server access
"""
                
                with open(main_readme, 'w') as f:
                    f.write(readme_content)
            
            logger.info("✅ Project structure created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Project structure creation failed: {e}")
            return False
    
    def validate_setup(self) -> Dict[str, bool]:
        """
        Validate the complete environment setup
        
        Returns:
            Dict[str, bool]: Validation results for each component
        """
        results = {}
        
        # Check .env file
        results["env_file"] = self.env_file_path.exists()
        
        # Check database connections
        results["client_database"] = self._test_database_connection("client")
        results["master_database"] = self._test_database_connection("master")
        
        # Check project structure
        required_folders = ["client_server", "master_server", "shared"]
        results["project_structure"] = all(
            (self.base_path / folder).exists() for folder in required_folders
        )
        
        # Overall status
        results["overall"] = all(results.values())
        
        return results
    
    def _test_database_connection(self, db_type: str) -> bool:
        """Test database connection using environment variables"""
        try:
            # Load environment variables
            from dotenv import load_dotenv
            load_dotenv(self.env_file_path)
            
            if db_type == "client":
                db_name = os.getenv("CLIENT_DB_NAME")
                db_user = os.getenv("CLIENT_DB_USER")
                db_pass = os.getenv("CLIENT_DB_PASS")
                db_host = os.getenv("CLIENT_DB_HOST")
                db_port = os.getenv("CLIENT_DB_PORT")
            else:  # master
                db_name = os.getenv("MASTER_DB_NAME")
                db_user = os.getenv("MASTER_DB_USER")
                db_pass = os.getenv("MASTER_DB_PASS")
                db_host = os.getenv("MASTER_DB_HOST")
                db_port = os.getenv("MASTER_DB_PORT")
            
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_pass,
                database=db_name
            )
            conn.close()
            return True
            
        except Exception:
            return False
    
    def run_complete_setup(self, 
                          admin_password: str = None,
                          db_user: str = "zyxczh",
                          db_password: str = "114514") -> bool:
        """
        Run the complete environment setup process
        
        Args:
            admin_password: PostgreSQL admin password
            db_user: Database user for applications
            db_password: Database password for applications
            
        Returns:
            bool: True if all setup steps successful
        """
        logger.info("🚀 Starting MyOral Master-Client Environment Setup")
        
        # Step 1: Setup databases
        logger.info("Step 1: Setting up database instances...")
        if not self.setup_database_instances(admin_password=admin_password):
            return False
        
        # Step 2: Setup environment variables
        logger.info("Step 2: Configuring environment variables...")
        if not self.setup_environment_variables(
            db_user=db_user, 
            db_password=db_password
        ):
            return False
        
        # Step 3: Create project structure
        logger.info("Step 3: Creating project structure...")
        if not self.create_project_structure():
            return False
        
        # Step 4: Validate setup
        logger.info("Step 4: Validating setup...")
        validation_results = self.validate_setup()
        
        if validation_results["overall"]:
            logger.info("✅ Complete environment setup successful!")
            logger.info("📋 Next steps:")
            logger.info("  1. Review .env file and update as needed")
            logger.info("  2. Move existing code to client_server folder")
            logger.info("  3. Implement master server database schema")
            logger.info("  4. Start development on master-client sync")
            return True
        else:
            logger.error("❌ Setup validation failed:")
            for component, status in validation_results.items():
                if not status:
                    logger.error(f"  - {component}: FAILED")
            return False


if __name__ == "__main__":
    """Run environment setup when executed directly"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MyOral Environment Setup")
    parser.add_argument("--admin-password", help="PostgreSQL admin password")
    parser.add_argument("--db-user", default="zyxczh", help="Database user")
    parser.add_argument("--db-password", default="114514", help="Database password")
    parser.add_argument("--base-path", help="Base project path")
    
    args = parser.parse_args()
    
    setup = EnvironmentSetup(base_path=args.base_path)
    success = setup.run_complete_setup(
        admin_password=args.admin_password,
        db_user=args.db_user,
        db_password=args.db_password
    )
    
    exit(0 if success else 1)
