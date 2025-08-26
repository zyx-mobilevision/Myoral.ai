#!/usr/bin/env python3
"""
Startup script for both master and client servers
Usage:
    python start_servers.py master    # Start master server only
    python start_servers.py client    # Start client server only  
    python start_servers.py both      # Start both servers
"""

import sys
import os
import subprocess
import time
import signal
from concurrent.futures import ThreadPoolExecutor
import threading

def start_master_server():
    """Start the master server"""
    print("🚀 Starting Master Server...")
    try:
        cmd = [sys.executable, "master_main.py"]
        return subprocess.Popen(cmd, cwd=os.path.dirname(__file__))
    except Exception as e:
        print(f"❌ Failed to start master server: {e}")
        return None

def start_client_server():
    """Start the client server"""
    print("🚀 Starting Client Server...")
    try:
        cmd = [sys.executable, "client_main.py"]
        return subprocess.Popen(cmd, cwd=os.path.dirname(__file__))
    except Exception as e:
        print(f"❌ Failed to start client server: {e}")
        return None

def wait_for_shutdown(processes):
    """Wait for shutdown signal and clean up processes"""
    def signal_handler(signum, frame):
        print("\n🔄 Shutting down servers...")
        for process in processes:
            if process and process.poll() is None:
                process.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Wait for all processes
        for process in processes:
            if process:
                process.wait()
    except KeyboardInterrupt:
        print("\n🔄 Received interrupt, shutting down...")
        for process in processes:
            if process and process.poll() is None:
                process.terminate()

def main():
    """Main startup function"""
    if len(sys.argv) < 2:
        print("Usage: python start_servers.py [master|client|both]")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    processes = []
    
    if mode == "master":
        process = start_master_server()
        if process:
            processes.append(process)
        else:
            sys.exit(1)
            
    elif mode == "client":
        process = start_client_server()
        if process:
            processes.append(process)
        else:
            sys.exit(1)
            
    elif mode == "both":
        # Start master server first
        master_process = start_master_server()
        if master_process:
            processes.append(master_process)
            time.sleep(2)  # Give master server time to start
        
        # Start client server
        client_process = start_client_server()
        if client_process:
            processes.append(client_process)
        
        if not processes:
            print("❌ Failed to start any servers")
            sys.exit(1)
    else:
        print("❌ Invalid mode. Use: master, client, or both")
        sys.exit(1)
    
    print("✅ Servers started successfully")
    print("Press Ctrl+C to stop all servers")
    
    # Wait for shutdown
    wait_for_shutdown(processes)

if __name__ == "__main__":
    main()
