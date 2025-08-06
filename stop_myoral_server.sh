#!/bin/bash

PROCESS_STR="uvicorn main:app --host 0.0.0.0 --port 8000"

echo "[MyOral Server stopping script]"
echo "Listing MyOral Server processe(s) running in background..."
processes=$(ps aux | grep myoral_backend | grep $PROCESS_STR | grep -v grep)

if [[ -n "$processes" ]]; then
    echo "$processes"
    echo "Killing MyOral Server processe ($PROCESS_STR) running in background..."
    pkill -f PROCESS_STR
    echo "MyOral Server processe(s) have been killed."
else
    echo "No MyOral Server processes found."
fi