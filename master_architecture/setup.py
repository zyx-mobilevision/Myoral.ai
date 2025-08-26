#!/usr/bin/env python3
"""
Quick setup script for MyOral Master-Client Architecture

This script provides an easy way to run the complete environment setup.
"""

import sys
import os
from pathlib import Path

# Add the utils directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "utils"))

from environment_setup import EnvironmentSetup


def main():
    """Main setup function with user interaction"""
    print("🏥 MyOral Master-Client Architecture Setup")
    print("=" * 50)
    
    # Get user inputs
    print("\nDatabase Configuration:")
    admin_password = input("PostgreSQL admin password (for database creation): ")
    
    print("\nApplication Database User:")
    db_user = input("Database username [zyxczh]: ").strip() or "zyxczh"
    db_password = input("Database password [114514]: ").strip() or "114514"
    
    print(f"\nStarting setup with:")
    print(f"  - Database user: {db_user}")
    print(f"  - Client database: oral_db_client")
    print(f"  - Master database: oral_db_master")
    
    confirm = input("\nProceed with setup? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Setup cancelled.")
        return
    
    # Run setup
    setup = EnvironmentSetup()
    success = setup.run_complete_setup(
        admin_password=admin_password,
        db_user=db_user,
        db_password=db_password
    )
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Review the generated .env file")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Move your existing MyOral code to the client_server folder")
        print("4. Start implementing the master server")
    else:
        print("\n❌ Setup failed. Check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
