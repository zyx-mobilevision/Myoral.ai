#!/bin/bash
#
# This script starts the MyOral Server using uvicorn
# Edit the PATH_TO_MYORAL_SERVER variable to point to your MyOral Server directory
PATH_TO_MYORAL_SERVER="/home/oral_backend/myoral_backend"


echo "[MyOral Server starting script]"
echo "Checking if MyOral Server is already running..."
if pgrep -f "uvicorn main:app" > /dev/null; then
    # Display message in blue
    echo -e "\033[0;34mMyOral Server is already running. Please stop it before starting a new instance.\033[0m"
    exit 1
fi
echo "Server path: $PATH_TO_MYORAL_SERVER"
cd $PATH_TO_MYORAL_SERVER || { echo "Failed to change directory to $PATH_TO_MYORAL_SERVER"; exit 1; }
# Activate myenv     
source myenv/bin/activate
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -e "Virtual environment activated successfully: \033[0;32m$VIRTUAL_ENV\033[0m"
else
    echo -e "\033[0;31mFailed to activate virtual environment.\033[0m"
    exit 1
fi
# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo -e "\033[0;31muvicorn is not installed. Please install it using 'pip install uvicorn'.\033[0m"
    exit 1
fi
# Start the server using nohup to keep it running in the background
# and redirect output to nohup.out
echo "Starting server with nohup..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
if [[ $? -eq 0 ]]; then
    echo -e "\033[0;32mServer started with nohup in the background.\033[0m"
else
    echo -e "\033[0;31mFailed to start server with nohup.\033[0m"
    exit 1
fi
