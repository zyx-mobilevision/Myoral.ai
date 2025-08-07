#!/bin/bash
# Call this script to start the MyOral server
# You may need to adjust the PATH_TO_MYORAL_SERVER or the SERVER_CMD variable if your server path or command line changes 
PATH_TO_MYORAL_SERVER="/home/oral_backend/myoral_backend"    
SERVER_CMD="uvicorn main:app --host 0.0.0.0 --port 8000"

echo "[MyOral Server starting script]"
echo "Checking if MyOral Server is already running..."
if pgrep -f "$SERVER_CMD" > /dev/null; then
    # Display message in blue
    echo -e "\033[0;34mMyOral Server is already running. Please stop it before starting a new instance.\033[0m"
    exit 1
fi

echo "Server path: $PATH_TO_MYORAL_SERVER"
cd $PATH_TO_MYORAL_SERVER || { echo "Failed to change directory to $PATH_TO_MYORAL_SERVER"; exit 1; }
# Activate myenv    
source myenv/bin/activate
if [[ "$VIRTUAL_ENV" != "" ]]; then
    # Display path in green color
    echo -e "Virtual environment activated successfully: \033[0;32m$PATH_TO_MYORAL_SERVER\033[0m"
else
    echo "Failed to activate virtual environment."
    exit 1
fi
# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo "uvicorn is not installed. Please install it using 'pip install uvicorn'."
    exit 1
fi
# Start the server using nohup to keep it running in the background
# and redirect output to nohup.out
echo "Starting server with nohup..."
nohup $SERVER_CMD &
if [[ $? -eq 0 ]]; then
    echo -e "\033[0;32mServer started with nohup in the background.\033[0m"
else
    echo "Failed to start server with nohup."
    exit 1
fi
