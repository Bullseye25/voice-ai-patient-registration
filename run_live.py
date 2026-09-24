"""
CareCloud Voice AI Agent - Live Runner
Starts FastAPI backend, launches Cloudflare Tunnel, automatically syncs Vapi webhook,
and displays reviewer testing instructions.
"""
import sys
import os
import re
import time
import signal
import subprocess
import shutil
import threading
from pathlib import Path

# Force unbuffered output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

# Load environment
try:
    import httpx
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

VAPI_API_KEY = os.getenv("VAPI_API_KEY", "2c6c775a-673d-4251-8006-763dc8492bd7")
ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "c42c2da7-e3b9-431b-ace5-a25bdc6b8f67")
PHONE_NUMBER = os.getenv("VAPI_PHONE_NUMBER", "+14632231253")


def find_cloudflared() -> str:
    """Finds path to cloudflared executable."""
    candidates = [
        shutil.which("cloudflared"),
        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
        r"C:\Program Files\cloudflared\cloudflared.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\cloudflared\cloudflared.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return "cloudflared"


def update_vapi_webhook(public_url: str):
    """Updates Vapi assistant serverUrl with the active public tunnel."""
    try:
        webhook_url = f"{public_url}/voice/webhook"
        headers = {
            "Authorization": f"Bearer {VAPI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {"serverUrl": webhook_url}
        res = httpx.patch(
            f"https://api.vapi.ai/assistant/{ASSISTANT_ID}",
            headers=headers,
            json=payload,
            timeout=10.0
        )
        if res.status_code == 200:
            return True, webhook_url
        return False, f"HTTP {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 75, flush=True)
    print("       CareCloud Voice AI Agent - Live Intake System", flush=True)
    print("       Lead Developer & Document Author: Ammad Raza", flush=True)
    print("=" * 75, flush=True)
    print("\n[1/3] Starting FastAPI Backend on http://127.0.0.1:8000...", flush=True)

    # 1. Start Uvicorn subprocess
    python_exe = sys.executable
    uvicorn_cmd = [
        python_exe, "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1", "--port", "8000"
    ]
    backend_proc = subprocess.Popen(
        uvicorn_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Wait for backend to be ready
    backend_ready = False
    for _ in range(10):
        time.sleep(1)
        try:
            r = httpx.get("http://127.0.0.1:8000/health", timeout=2.0)
            if r.status_code == 200:
                backend_ready = True
                break
        except Exception:
            pass

    if not backend_ready:
        print("[ERROR] FastAPI backend failed to start.", flush=True)
        sys.exit(1)
    print("      -> FastAPI backend is running and healthy.", flush=True)

    # 2. Start Cloudflare Tunnel
    print("\n[2/3] Establishing secure public HTTPS tunnel...", flush=True)
    cloudflared_exe = find_cloudflared()
    tunnel_cmd = [cloudflared_exe, "tunnel", "--url", "http://127.0.0.1:8000"]

    tunnel_proc = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )

    public_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Read output until tunnel URL is found (up to 30 seconds)
    start_time = time.time()
    while time.time() - start_time < 30:
        line = tunnel_proc.stdout.readline()
        if not line and tunnel_proc.poll() is not None:
            break
        match = url_pattern.search(line)
        if match:
            public_url = match.group(0)
            break

    if not public_url:
        print("[WARNING] Could not parse trycloudflare URL automatically. Using cached URL.", flush=True)
        public_url = os.getenv("WEBHOOK_BASE_URL", "https://soldiers-educated-maintains-beauty.trycloudflare.com")
    else:
        print(f"      -> Public tunnel active: {public_url}", flush=True)

    # 3. Sync Vapi Assistant Webhook
    print("\n[3/3] Synchronizing Vapi Voice Assistant webhook...", flush=True)
    success, details = update_vapi_webhook(public_url)
    if success:
        print(f"      -> Vapi Assistant synced: {details}", flush=True)
    else:
        print(f"      -> Notice: {details}", flush=True)

    # Display Ready Information
    formatted_phone = "+1 (463) 223-1253"
    print("\n" + "#" * 75, flush=True)
    print(f"  SYSTEM STATUS: ONLINE & READY FOR CALLS", flush=True)
    print(f"  Dialable Phone Number: {formatted_phone}", flush=True)
    print(f"  Public REST API:       {public_url}", flush=True)
    print(f"  Interactive Docs:      {public_url}/docs", flush=True)
    print("#" * 75, flush=True)

    print("\n" + "-" * 75, flush=True)
    print("  HOW TO TEST OVER THE PHONE:", flush=True)
    print(f"  1. Call {formatted_phone} from your phone.", flush=True)
    print("  2. Alex will answer: \"Thank you for calling CareCloud Patient Registration!", flush=True)
    print("     My name is Alex. I can help you register as a new patient today...\"", flush=True)
    print("  3. Provide your name, birth date, sex, 10-digit phone, and street address.", flush=True)
    print("  4. Listen as Alex reads back all your information to confirm.", flush=True)
    print("  5. Say \"Yes, that is correct\".", flush=True)
    print("  6. Alex will save your registration and close gracefully: \"You're all set!\"", flush=True)
    print(f"  7. Open {public_url}/patients in your browser to verify", flush=True)
    print("     your record appears in the database!", flush=True)
    print("\n  BONUS TEST (Duplicate Detection):", flush=True)
    print(f"  - Call back from the same phone number.", flush=True)
    print("  - Alex recognizes you: \"It looks like we already have a record for [Name].", flush=True)
    print("    Would you like to update your information instead?\"", flush=True)
    print("-" * 75, flush=True)
    print("\n[SYSTEM RUNNING] Press Ctrl+C in this terminal window to stop servers.\n", flush=True)

    def shutdown(sig, frame):
        print("\nShutting down servers...", flush=True)
        try:
            backend_proc.terminate()
            tunnel_proc.terminate()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep alive loop
    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("Backend stopped.", flush=True)
                break
            if tunnel_proc.poll() is not None:
                print("Tunnel stopped.", flush=True)
                break
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
