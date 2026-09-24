"""
CareCloud Voice AI Agent - Live Runner
Starts FastAPI backend with automatic port failover, launches public tunnel (carecloud-voice-ai),
automatically syncs Vapi webhook, and displays reviewer testing instructions.
"""
import sys
import os
import re
import time
import signal
import socket
import subprocess
import shutil
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
PREFERRED_SUBDOMAIN = "carecloud-voice-ai"


def find_available_port(start_port: int = 8000, max_attempts: int = 50) -> int:
    """
    Checks if start_port is available. If occupied, iterates to find the next free port.
    """
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue

    # Fallback: ask OS for any available ephemeral port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


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


def start_tunnel(port: int):
    """Starts localtunnel with custom subdomain or falls back to Cloudflare."""
    lt_script = Path("node_modules/localtunnel/bin/lt.js")
    if lt_script.exists():
        node_cmd = shutil.which("node") or "node"
        lt_cmd = [node_cmd, str(lt_script), "--port", str(port), "--subdomain", PREFERRED_SUBDOMAIN]
        try:
            proc = subprocess.Popen(
                lt_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            time.sleep(2)
            expected_url = f"https://{PREFERRED_SUBDOMAIN}.loca.lt"
            return proc, expected_url
        except Exception:
            pass

    # Fallback to Cloudflare Tunnel
    cloudflared_exe = find_cloudflared()
    tunnel_cmd = [cloudflared_exe, "tunnel", "--url", f"http://127.0.0.1:{port}"]
    proc = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    start = time.time()
    while time.time() - start < 30:
        line = proc.stdout.readline()
        match = url_pattern.search(line)
        if match:
            return proc, match.group(0)
    return proc, f"https://{PREFERRED_SUBDOMAIN}.loca.lt"


def main():
    print("=" * 75, flush=True)
    print("       CareCloud Voice AI Agent - Live Intake System", flush=True)
    print("       Lead Developer & Document Author: Ammad Raza", flush=True)
    print("=" * 75, flush=True)

    # 0. Port Selection & Automatic Fallback
    target_port = int(os.getenv("PORT", 8000))
    selected_port = find_available_port(target_port)

    if selected_port != target_port:
        print(f"\n[NOTICE] Port {target_port} is busy. Automatically switched to available port {selected_port}.", flush=True)
    else:
        print(f"\n[PORT] Using port {selected_port}.", flush=True)

    print(f"\n[1/3] Starting FastAPI Backend on http://127.0.0.1:{selected_port}...", flush=True)

    # 1. Start Uvicorn subprocess on selected_port
    python_exe = sys.executable
    uvicorn_cmd = [
        python_exe, "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1", "--port", str(selected_port)
    ]
    backend_proc = subprocess.Popen(
        uvicorn_cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Wait for backend to be ready
    backend_ready = False
    for _ in range(10):
        time.sleep(1)
        try:
            r = httpx.get(f"http://127.0.0.1:{selected_port}/health", timeout=2.0)
            if r.status_code == 200:
                backend_ready = True
                break
        except Exception:
            pass

    if not backend_ready:
        print("[ERROR] FastAPI backend failed to start.", flush=True)
        sys.exit(1)
    print("      -> FastAPI backend is running and healthy.", flush=True)

    # 2. Start Public Tunnel forwarding to selected_port
    print(f"\n[2/3] Establishing public tunnel on subdomain '{PREFERRED_SUBDOMAIN}' (forwarding port {selected_port})...", flush=True)
    tunnel_proc, public_url = start_tunnel(selected_port)
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
    print(f"  Local Port:            {selected_port}", flush=True)
    print(f"  Custom Subdomain:      https://carecloud-voice-ai.loca.lt", flush=True)
    print(f"  Dialable Phone Number: {formatted_phone}", flush=True)
    print(f"  Public REST API:       {public_url}/patients", flush=True)
    print(f"  Interactive Docs:      {public_url}/docs", flush=True)
    print("#" * 75, flush=True)

    print("\n" + "-" * 75, flush=True)
    print("  HOW TO TEST OVER THE PHONE:", flush=True)
    print(f"  1. Call {formatted_phone} from your phone.")
    print("  2. Alex will answer: \"Thank you for calling CareCloud Patient Registration!")
    print("     My name is Alex. I can help you register as a new patient today...\"")
    print("  3. Provide your name, birth date, sex, 10-digit phone, and street address.")
    print("  4. Listen as Alex reads back all your information to confirm.")
    print("  5. Say \"Yes, that is correct\".")
    print("  6. Alex will save your registration and close gracefully: \"You're all set!\"")
    print(f"  7. Open {public_url}/patients in your browser to verify")
    print("     your record appears in the database!")
    print("\n  BONUS TEST (Duplicate Detection):")
    print(f"  - Call back from the same phone number.")
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

    # Keep alive loop with auto-reconnect watchdog
    failed_checks = 0
    try:
        last_health_check = time.time()
        while True:
            time.sleep(2)
            if backend_proc.poll() is not None:
                print("Backend stopped.", flush=True)
                break

            # Watchdog: verify tunnel process is alive
            if tunnel_proc.poll() is not None:
                print("\n[WATCHDOG] Tunnel process exited. Restarting tunnel...", flush=True)
                tunnel_proc, public_url = start_tunnel(selected_port)
                update_vapi_webhook(public_url)
                print(f"      -> Reconnected: {public_url}", flush=True)

            now = time.time()
            if now - last_health_check > 45:
                last_health_check = now
                try:
                    r = httpx.get(
                        f"{public_url}/health",
                        headers={"bypass-tunnel-reminder": "true"},
                        timeout=6.0
                    )
                    if r.status_code != 200:
                        failed_checks += 1
                    else:
                        failed_checks = 0
                except Exception:
                    failed_checks += 1

                if failed_checks >= 3:
                    print("\n[WATCHDOG] Subdomain unresponsive after 3 attempts. Reconnecting...", flush=True)
                    failed_checks = 0
                    try:
                        tunnel_proc.terminate()
                    except Exception:
                        pass
                    tunnel_proc, public_url = start_tunnel(selected_port)
                    update_vapi_webhook(public_url)
                    print(f"      -> Reconnected: {public_url}", flush=True)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
