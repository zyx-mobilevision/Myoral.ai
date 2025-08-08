#!/bin/bash
# Call this script to start the MyOral server
# You may need to adjust the PATH_TO_MYORAL_SERVER or the SERVER_CMD variable if your server path or command line changes 

# Use this to check if server is currently running:  
# ps aux | grep --color=always myoral_backend | grep -v grep

PATH_TO_MYORAL_SERVER="/home/myoral/dev/myoral_backend"    
# HTTP:
SERVER_CMD="uvicorn main:app --host 0.0.0.0 --port 8000"
# HTTPS:
SERVER_CMD="uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-keyfile $PATH_TO_MYORAL_SERVER/key.pem --ssl-certfile $PATH_TO_MYORAL_SERVER/cert.pem"

echo "[MyOral Server starting script]"
echo "Checking if MyOral Server is already running..."
if pgrep -f "$SERVER_CMD" > /dev/null; then
    # Display message in blue
    echo -e "\033[0;34mMyOral Server is already running. Please stop it before starting a new instance.\033[0m"
    exit 1
fi

# check if key.pem and cert.pem exist
if [[ -f "$PATH_TO_MYORAL_SERVER/key.pem" && -f "$PATH_TO_MYORAL_SERVER/cert.pem" ]]; then
    echo -e "\033[0;32mSSL key and certificate files found:\033[0m"
    echo -e "\033[0;32m  $PATH_TO_MYORAL_SERVER/key.pem\033[0m"
    echo -e "\033[0;32m  $PATH_TO_MYORAL_SERVER/cert.pem\033[0m"
else
    echo "SSL key or certificate files not found in $PATH_TO_MYORAL_SERVER. Please ensure they exist."
    exit 1
fi

echo "Server path: $PATH_TO_MYORAL_SERVER"
cd $PATH_TO_MYORAL_SERVER || { echo "Failed to change directory to $PATH_TO_MYORAL_SERVER"; exit 1; }
# Activate myoral_venv    
source myoral_venv/bin/activate
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
echo "nohup $SERVER_CMD &"
nohup $SERVER_CMD &
if [[ $? -eq 0 ]]; then
    echo -e "\033[0;32mServer started with nohup in the background.\033[0m"
else
    echo "Failed to start server with nohup."
    exit 1
fi
