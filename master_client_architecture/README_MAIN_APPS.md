# MyOral Master-Client Server Applications

This directory contains the main entry point applications for the MyOral master-client architecture.

## 📁 Main Application Files

### `master_main.py` - Master Server Application
**Purpose:** Analytics and monitoring server for aggregated dental health data

**Features:**
- FastAPI application with comprehensive analytics endpoints
- Thread-safe database operations with SQLite/WAL mode
- API key authentication and client management
- Health monitoring and system status
- CORS configuration for web frontend
- Comprehensive logging and error handling
- Graceful startup/shutdown with lifespan management

**Endpoints:**
- `GET /` - Server information
- `GET /health` - Basic health check
- `GET /api/health/detailed` - Detailed system health
- `GET /api/analytics/*` - Analytics endpoints (requires API key)
- `POST /api/auth/request-api-key` - API key management

### `client_main.py` - Client Server Application  
**Purpose:** Patient data management and local dental health operations

**Features:**
- FastAPI application for patient data operations
- Integration with existing MyOral routers (commented for template)
- Background synchronization with master server
- Local PII and medical data storage
- Static file serving for uploaded photos
- Sync management endpoints
- Health monitoring with sync status

**Endpoints:**
- `GET /` - Server information
- `GET /health` - Basic health check  
- `GET /api/health/detailed` - Detailed health with sync status
- `POST /api/sync/manual` - Trigger manual sync
- `GET /api/sync/status` - Current sync status
- All existing MyOral endpoints (to be integrated)

## 🚀 Running the Servers

### Individual Server Startup

**Master Server:**
```bash
python master_main.py
```
- Default: http://localhost:8001
- Environment: `MASTER_SERVER_PORT`, `MASTER_SERVER_HOST`

**Client Server:**  
```bash
python client_main.py
```
- Default: http://localhost:8000
- Environment: `CLIENT_SERVER_PORT`, `CLIENT_SERVER_HOST`

### Automated Startup Script

```bash
# Start master server only
python start_servers.py master

# Start client server only  
python start_servers.py client

# Start both servers
python start_servers.py both
```

### Production Deployment

**Using Uvicorn directly:**
```bash
# Master server
uvicorn master_main:app --host 0.0.0.0 --port 8001 --workers 4

# Client server
uvicorn client_main:app --host 0.0.0.0 --port 8000 --workers 2
```

**Using Gunicorn (production):**
```bash
# Master server
gunicorn -w 4 -k uvicorn.workers.UvicornWorker master_main:app --bind 0.0.0.0:8001

# Client server  
gunicorn -w 2 -k uvicorn.workers.UvicornWorker client_main:app --bind 0.0.0.0:8000
```

## ⚙️ Configuration

### Environment Variables

**Database Configuration:**
```env
# Master Server Database
MASTER_DB_HOST=localhost
MASTER_DB_PORT=5432
MASTER_DB_NAME=oral_db_master
MASTER_DB_USER=zyxczh
MASTER_DB_PASS=114514

# Client Server Database  
CLIENT_DB_HOST=localhost
CLIENT_DB_PORT=5432
CLIENT_DB_NAME=oral_db_client
CLIENT_DB_USER=zyxczh
CLIENT_DB_PASS=114514
```

**Server Configuration:**
```env
# Master Server
MASTER_SERVER_HOST=0.0.0.0
MASTER_SERVER_PORT=8001
MASTER_SERVER_SALT=myoral_secure_salt_2025_v1

# Client Server
CLIENT_SERVER_HOST=0.0.0.0
CLIENT_SERVER_PORT=8000
CLIENT_ID=client_001

# Sync Configuration
MASTER_SERVER_URL=http://localhost:8001
MASTER_API_KEY=client_001_key
SYNC_INTERVAL_MINUTES=30
```

**Development:**
```env
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## 🔒 Security Features

### Master Server
- API key authentication for all analytics endpoints
- Client permission verification
- No PII or medical data storage
- CORS configuration for frontend access
- Comprehensive audit logging

### Client Server
- Local storage of sensitive medical data
- Automatic data anonymization before sync
- Background sync with retry logic
- Secure token handling
- Static file protection

## 📊 Monitoring & Health Checks

### Health Check Endpoints

**Basic Health:**
- Master: `GET http://localhost:8001/health`
- Client: `GET http://localhost:8000/health`

**Detailed Health:**
- Master: `GET http://localhost:8001/api/health/detailed`
  - Database connection status
  - System health metrics
  - Connection pool utilization
- Client: `GET http://localhost:8000/api/health/detailed`
  - Database connection status
  - Sync service status
  - Last sync information

### Logging

**Log Files:**
- `master_server.log` - Master server operations
- `client_server.log` - Client server operations

**Log Levels:**
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Critical errors requiring attention

## 🔄 Integration with Existing MyOral Code

To integrate with your existing MyOral application:

1. **Move existing files to client_server folder:**
   ```bash
   # Copy your current MyOral files
   cp -r ../Myoral.ai/* ./client_server/
   ```

2. **Update client_main.py imports:**
   ```python
   # Uncomment and update these lines in client_main.py
   from routers import (
       register, login, photoUpload, update, analyze, 
       retrieve, reminder, print, oral_report_pdf
   )
   ```

3. **Add sync calls to existing endpoints:**
   ```python
   # In your existing routers, add sync triggers
   from services.sync_service import ClientSyncService
   
   # After user registration/update
   await sync_service.sync_user_data(user_data)
   ```

## 🐳 Docker Deployment (Future)

```dockerfile
# Example Dockerfile for master server
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["python", "master_main.py"]
```

## 📝 Next Steps

1. **Complete Integration:** Move existing MyOral code to client_server structure
2. **Add Sync Triggers:** Integrate sync calls in existing endpoints  
3. **Deploy Master Server:** Set up dedicated master server for analytics
4. **Configure Networking:** Set up proper networking between servers
5. **Add Monitoring:** Implement comprehensive monitoring and alerting
