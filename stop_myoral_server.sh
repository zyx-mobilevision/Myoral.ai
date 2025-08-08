#!/bin/bash
# Call this script to stop the MyOral server
# You may need to adjust the PROCESS_STR variable if your server command changes
PROCESS_STR="uvicorn main:app --host 0.0.0.0 --port 8000"
PATH_TO_MYORAL_SERVER="/home/myoral/dev/myoral_backend" 
PROCESS_STR="uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-keyfile $PATH_TO_MYORAL_SERVER/key.pem --ssl-certfile $PATH_TO_MYORAL_SERVER/cert.pem"
PROCESS_STR="python3 /home/myoral/dev/myoral_backend/myoral_venv/bin/uvicorn main:app"

echo "[MyOral Server stopping script]"
processes=$(ps aux | grep myoral_backend | grep uvicorn | grep -v grep)

if [[ -n "$processes" ]]; then
    echo -e "Found process: \033[0;32m$processes\033[0m"
    pids=$(echo "$processes" | awk '{print $2}')
    echo -e "Killing MyOral Server process IDs: \033[0;31m$pids\033[0m"
    kill -9 $pids
    echo "MyOral Server process has been killed."
else
    echo "No MyOral Server processes found."
fi