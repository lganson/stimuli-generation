#!/usr/bin/env python3
"""
Launcher script for Figure-Ground Stimulus Generator GUI.
Starts local HTTP backend server and automatically opens the application in default web browser.
"""

import sys
import os
import time
import webbrowser
import threading

def open_browser(port):
    time.sleep(0.8)
    url = f"http://localhost:{port}"
    print(f"Opening GUI in web browser: {url}")
    webbrowser.open(url)

def main():
    port = 5000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])

    # Start browser in background thread
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # Import and run server
    from gui_backend import run_server
    run_server(port)

if __name__ == '__main__':
    main()
