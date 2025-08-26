# Environment Setup for MyOral Master-Client Architecture

This utility sets up the complete development environment for the MyOral master-client architecture.

## Features

- **Database Setup**: Creates separate PostgreSQL databases for client and master servers
- **Environment Configuration**: Generates comprehensive .env file with all required settings
- **Project Structure**: Creates organized folder structure for master-client development
- **Validation**: Validates the complete setup to ensure everything works

## Usage

### Quick Setup (Interactive)

```bash
python setup.py
```

### Command Line Setup

```bash
python utils/environment_setup.py --admin-password YOUR_POSTGRES_PASSWORD
```

### Programmatic Usage

```python
from utils.environment_setup import EnvironmentSetup

setup = EnvironmentSetup()
success = setup.run_complete_setup(
    admin_password="your_postgres_password",
    db_user="your_db_user", 
    db_password="your_db_password"
)
```

## What Gets Created

### Databases
- `oral_db_client` - Client server database (for existing MyOral app)
- `oral_db_master` - Master server database (analytics only)

### Environment Variables (.env)
- Database connection settings for both servers
- Master server configuration (salt, client ID, URLs)
- Security settings (JWT, API keys)
- MQTT configuration for real-time sync
- Development/production settings

### Project Structure
```
myoral_backend/
├── client_server/          # Existing MyOral app goes here
├── master_server/          # New master server implementation
├── shared/                 # Common utilities and models
├── scripts/                # Setup and maintenance scripts
├── config/                 # Configuration files
└── docs/                   # Documentation
```

## Requirements

- PostgreSQL server running
- Python 3.7+
- Required packages: `pip install -r requirements.txt`

## Security Features

- Separate databases ensure data isolation
- Master server only gets anonymized data
- Configurable API key expiration
- Secure password hashing with salt
- Environment-based configuration

## Next Steps After Setup

1. **Review Configuration**: Check the generated `.env` file and update as needed
2. **Move Existing Code**: Move your current MyOral FastAPI app to `client_server/`
3. **Install Dependencies**: Run `pip install -r requirements.txt`
4. **Implement Master Server**: Start building the master server in `master_server/`
5. **Setup Sync**: Implement data synchronization between client and master

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Check admin credentials
- Verify host and port settings

### Permission Issues
- Ensure the user has database creation privileges
- Check file system permissions for project directory

### Import Errors
- Install required packages: `pip install psycopg2-binary python-dotenv`
- Ensure Python path includes the utils directory

## Validation

The setup includes automatic validation of:
- Database connections
- Environment file creation
- Project structure
- Overall setup integrity

Run validation separately:
```python
setup = EnvironmentSetup()
results = setup.validate_setup()
print(results)
```
