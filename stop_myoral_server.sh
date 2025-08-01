#!/bin/bash
echo "[MyOral Server stopping script]"
echo "Listing MyOral Server processe(s) running in background..."
processes=$(ps aux | grep myoral_backend | grep -v grep)

if [[ -n "$processes" ]]; then
    echo "$processes"
    echo "Killing MyOral Server processe(s) running in background..."
    pkill -f "uvicorn main:app"
    echo "MyOral Server processe(s) have been killed."
else
    echo "No MyOral Server processes found."
fi