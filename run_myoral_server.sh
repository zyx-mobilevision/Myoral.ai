#!/bin/bash
echo "[MyOral Server starting script]"
PATH_TO_MYORAL_SERVER="/home/oral_backend/myoral_backend"    
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
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
if [[ $? -eq 0 ]]; then
    echo -e "\033[0;32mServer started with nohup in the background.\033[0m"
else
    echo "Failed to start server with nohup."
    exit 1
fi
