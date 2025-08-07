#!/bin/bash
# Call this script to stop the MyOral server
# You may need to adjust the PROCESS_STR variable if your server command changes
PROCESS_STR="uvicorn main:app --host 0.0.0.0 --port 8000"

echo "[MyOral Server stopping script]"
processes=$(ps aux | grep myoral_backend | grep "$PROCESS_STR" | grep -v grep)

if [[ -n "$processes" ]]; then
    echo -e "Found process: \033[0;32m$processes\033[0m"
    echo -e "Killing MyOral Server process (\033[0;31m$PROCESS_STR\033[0m) running in background..."
    pkill -f "$PROCESS_STR"
    echo "MyOral Server process has been killed."
else
    echo "No MyOral Server processes found."
fi