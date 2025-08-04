#!/bin/bash
echo "[MyOral Server starting script]"
PATH_TO_MYORAL_SERVER="/home/oral_backend/myoral_backend"    
echo "Server path: $PATH_TO_MYORAL_SERVER"
cd $PATH_TO_MYORAL_SERVER || { echo "Failed to change directory to $PATH_TO_MYORAL_SERVER"; exit 1; }
# Activate myenv    
source myenv/bin/activate
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "Virtual environment activated successfully: $VIRTUAL_ENV"
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
    echo "Server started with nohup in the background."
else
    echo "Failed to start server with nohup."
    exit 1
fi
