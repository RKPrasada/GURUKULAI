#!/usr/bin/env python3
"""
VidyaBot Desktop Launcher (React Frontend)
Starts FastAPI backend + React frontend in development mode.
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).parent
WEB_DIR = BASE_DIR / "web"

os.chdir(BASE_DIR)

if (BASE_DIR / ".env").exists():
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")

API_PORT = int(os.getenv("API_PORT", "8000"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "3000"))
API_URL = f"http://localhost:{API_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"

os.environ["API_BASE_URL"] = API_URL


def _wait_for_port(port: int, timeout: int = 30) -> bool:
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def start_api():
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app",
         "--host", "0.0.0.0", "--port", str(API_PORT), "--reload"],
        cwd=BASE_DIR,
    )
    print(f"API server starting on {API_URL} ...")


def start_frontend():
    subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=WEB_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print(f"React frontend starting on {FRONTEND_URL} ...")


def main():
    print("=" * 50)
    print("  📚 VidyaBot — AI Tutor for Indian Exams")
    print("=" * 50)
    print("🚀 React Frontend Edition\n")

    start_api()
    start_frontend()

    print("Waiting for services to start...")
    if _wait_for_port(API_PORT):
        print(f"✅ API ready at {API_URL}")
    else:
        print(f"⚠️  API may not have started correctly")

    if _wait_for_port(FRONTEND_PORT):
        print(f"✅ Frontend ready at {FRONTEND_URL}")
        webbrowser.open(FRONTEND_URL)
    else:
        print(f"⚠️  Frontend may not have started. Open {FRONTEND_URL} manually.")

    print("\n" + "=" * 50)
    print("VidyaBot is running!")
    print("=" * 50)
    print(f"📱 Frontend: {FRONTEND_URL}")
    print(f"🔧 API:      {API_URL}")
    print(f"📖 API Docs: {API_URL}/docs")
    print("\nPress Ctrl+C to stop all services.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down VidyaBot...")


if __name__ == "__main__":
    main()
