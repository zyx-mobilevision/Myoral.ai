"""
Phase 1 Master-Client Architecture Package

This package provides the architectural foundation for splitting a monolithic 
MyOral database into a secure master-client system with HIPAA compliance.

Key Components:
- core: Data classification and anonymization
- models: Pydantic models and response schemas  
- database: Database operations and schema planning
- services: Sync services and background schedulers
- api: FastAPI endpoints for master and client servers
- utils: Application factories and utilities
"""

from .core import DataClassification, DataAnonymizationStrategy
from .models import *
from .database import DatabaseManager, DatabaseSchemaPlanning
from .services import ClientSyncService, BackgroundSyncScheduler
from .api import MasterServerAPIDesign, ClientServerAPIDesign
from .utils import create_master_server_app, create_client_server_app

__version__ = "1.0.0"
__author__ = "MyOral Architecture Team"

__all__ = [
    # Core functionality
    "DataClassification",
    "DataAnonymizationStrategy",
    
    # Database
    "DatabaseManager", 
    "DatabaseSchemaPlanning",
    
    # Services
    "ClientSyncService",
    "BackgroundSyncScheduler",
    
    # API
    "MasterServerAPIDesign",
    "ClientServerAPIDesign",
    
    # Utilities
    "create_master_server_app",
    "create_client_server_app"
]
