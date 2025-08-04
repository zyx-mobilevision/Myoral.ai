#!/bin/bash
echo "[MyOral Server starting script]"
# Activate myenv    
echo "Activating enviorment..."
source myenv/bin/activate
# Navigate to the directory where the MyOral server is located
echo "Starting MyOral Server for public use..."

read -p "Would you like to use 'nohup' to run the server in the background? (y/n) [Y]: " use_nohup
use_nohup=${use_nohup:-y}

if [[ "$use_nohup" == "y" || "$use_nohup" == "Y" ]]; then
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 &

    echo "Server started with nohup in the background."
else
    uvicorn main:app --host 0.0.0.0 --port 8000
fi