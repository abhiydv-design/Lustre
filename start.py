#!/usr/bin/env python3
"""Start Jewellery Image Studio with one command.

    python start.py            run on this computer (opens the app in your browser)
    python start.py --phone    also make an https link you can open on your phone
    python start.py --setup    only install and create backend/.env, then stop
    python start.py --test     run the automated tests

The first run creates a private Python environment in backend/.venv, installs what's
needed and writes backend/.env with safe test settings (no AI keys, no real payments).
Later runs start in seconds. To use real AI backgrounds, see backend/.env.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
VENV = BACKEND / ".venv"
ENV_FILE = BACKEND / ".env"
STAMP = VENV / ".installed"


def say(msg: str = "") -> None:
    print(msg, flush=True)


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def in_venv() -> bool:
    return Path(sys.prefix).resolve() == VENV.resolve()


def read_env() -> dict[str, str]:
    out = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                out[k.strip()] = v.split(" #", 1)[0].strip().strip('"').strip("'")
    return out


def write_env() -> None:
    """Test-mode settings that work with no accounts or keys."""
    admin = secrets.token_hex(12)  # letters and digits only: easy to copy
    ENV_FILE.write_text(f"""# Jewellery Image Studio settings. Created by start.py; edit freely, then restart.
# Full list with explanations: backend/.env.example

# ---------- Test mode (works with no keys) ----------
DEV_MODE=1                 # sign-in codes appear on screen instead of SMS; payments complete instantly
SECRET_KEY={secrets.token_urlsafe(32)}
CUTOUT_PROVIDER=threshold  # simple cut-out; works for photos on a plain light background
SCENE_PROVIDER=mock        # plain gradient backgrounds instead of AI scenes
UPSCALE_PROVIDER=lanczos   # simple enlargement instead of AI upscaling

# Example prices so the Buy buttons work in test mode (₹). Change once pricing is decided.
PACK_STARTER_PRICE_INR=249
PACK_SHOP_PRICE_INR=999
PACK_STUDIO_PRICE_INR=

# Team console at /admin. Your token is the part after "admin:".
ADMIN_TOKENS=admin:{admin}

# ---------- Real AI backgrounds ----------
# 1. Create an account at replicate.com, add billing, copy your API token.
# 2. Replace the three provider lines above with:
#      CUTOUT_PROVIDER=rembg      (AI cut-out; needs about 1.3 GB of free memory)
#      SCENE_PROVIDER=replicate
#      UPSCALE_PROVIDER=replicate
# 3. Set your token below and run start.py again (it installs the AI packages by itself).
REPLICATE_API_TOKEN=
COST_PER_SCENE_INR=0       # your Replicate price per background, for cost-per-image metrics
COST_PER_UPSCALE_INR=0

# ---------- Real payments (Razorpay) ----------
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
""", encoding="utf-8")


def needs_ai(env: dict[str, str]) -> bool:
    if env.get("AI_MODE", "").lower() == "real" and not env.get("CUTOUT_PROVIDER"):
        return True
    return env.get("CUTOUT_PROVIDER") == "rembg" or "replicate" in (env.get("SCENE_PROVIDER"), env.get("UPSCALE_PROVIDER"))


def install(env: dict[str, str]) -> None:
    files = [BACKEND / "requirements.txt"] + ([BACKEND / "requirements-ai.txt"] if needs_ai(env) else [])
    digest = hashlib.sha256(b"".join(f.read_bytes() for f in files)).hexdigest()
    if STAMP.exists() and STAMP.read_text() == digest:
        return
    say("Installing (first run takes a few minutes)…" if not STAMP.exists() else "Updating packages…")
    py = str(venv_python())
    subprocess.run([py, "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=True)
    for f in files:
        subprocess.run([py, "-m", "pip", "install", "--quiet", "-r", str(f)], check=True)
    STAMP.write_text(digest)


def bootstrap(argv: list[str]) -> None:
    """Create the environment and settings if needed, then re-run this script inside the environment."""
    if sys.version_info < (3, 11):
        sys.exit(f"Python 3.11 or newer is needed (you have {sys.version.split()[0]}). Get it from python.org.")
    if not ENV_FILE.exists():
        write_env()
        say(f"Created {ENV_FILE.relative_to(ROOT)} with test settings.")
    if not venv_python().exists():
        say("Creating a private Python environment in backend/.venv…")
        venv.create(VENV, with_pip=True)
    install(read_env())
    if not in_venv():
        sys.exit(subprocess.call([str(venv_python()), str(Path(__file__).resolve()), *argv]))


def wait_healthy(url: str, proc: subprocess.Popen, seconds: int = 60) -> bool:
    for _ in range(seconds * 4):
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:  # noqa: BLE001 - not up yet
            time.sleep(0.25)
    return False


def start_tunnel(port: int) -> tuple[subprocess.Popen | None, str | None]:
    exe = shutil.which("cloudflared")
    if not exe:
        say("\nTo open it on your phone, install Cloudflare's free tunnel tool, then run start.py --phone again:")
        say("  Mac:     brew install cloudflared")
        say("  Windows: winget install --id Cloudflare.cloudflared")
        say("  Linux:   see https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        return None, None
    proc = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    found: list[str] = []

    def read() -> None:
        for line in proc.stdout:  # keep draining so the tunnel never blocks
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if m and not found:
                found.append(m.group(0))

    threading.Thread(target=read, daemon=True).start()
    for _ in range(120):
        if found or proc.poll() is not None:
            break
        time.sleep(0.25)
    return proc, (found[0] if found else None)


def main() -> None:
    ap = argparse.ArgumentParser(description="Start Jewellery Image Studio.")
    ap.add_argument("--phone", action="store_true", help="also create an https link for your phone")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true", help="don't open the browser")
    ap.add_argument("--setup", action="store_true", help="install and create settings, then stop")
    ap.add_argument("--test", action="store_true", help="run the automated tests")
    args = ap.parse_args()

    bootstrap(sys.argv[1:])  # exits here unless we're already inside backend/.venv
    if args.setup:
        say("Setup complete. Start with: python start.py")
        return
    if args.test:
        sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q"], cwd=BACKEND))

    env = read_env()
    if needs_ai(env) and not env.get("REPLICATE_API_TOKEN") and "replicate" in (env.get("SCENE_PROVIDER"), env.get("UPSCALE_PROVIDER")):
        say("Warning: .env uses Replicate but REPLICATE_API_TOKEN is empty, so AI images will fail (and be refunded).")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0",
                               "--port", str(args.port), "--proxy-headers", "--forwarded-allow-ips", "*"], cwd=BACKEND)
    local = f"http://localhost:{args.port}"
    tunnel = None
    try:
        if not wait_healthy(local + "/health", server):
            sys.exit(f"The server didn't start. Is port {args.port} already in use? Try: python start.py --port 8001")
        phone_url = None
        if args.phone:
            tunnel, phone_url = start_tunnel(args.port)
        token = (env.get("ADMIN_TOKENS", "").split(",")[0].partition(":")[2]) or None
        mode = "real AI" if needs_ai(env) else "test mode (gradient backgrounds, codes on screen, instant payments)"
        say("\n" + "=" * 64)
        say("  Jewellery Image Studio is running: " + mode)
        say("=" * 64)
        say(f"  App on this computer:  {local}/app")
        if phone_url:
            say(f"  App on your phone:     {phone_url}/app")
            say("     (anyone with this link can use it while this window is open)")
        say(f"  Team console:          {local}/admin" + (f"   token: {token}" if token else "   (set ADMIN_TOKENS in backend/.env)"))
        say(f"  API documentation:     {local}/docs")
        say("  Settings:              backend/.env  (restart after editing)")
        say("  Stop:                  Ctrl+C")
        say("=" * 64 + "\n")
        if not args.no_browser:
            webbrowser.open(local + "/app")
        server.wait()
    except KeyboardInterrupt:
        say("\nStopping…")
    finally:
        for proc in (tunnel, server):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    main()
