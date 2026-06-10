"""
cli.py — Helix CLI
One-command setup for the Helix autonomous CI/CD healing agent.
Usage: python cli.py init
"""

import os
import sys
import time
import signal
import secrets
import subprocess
import threading
import webbrowser
from pathlib import Path

import requests
from github import Github, GithubException
from dotenv import set_key, load_dotenv

# ── Constants ────────────────────────────────────────────────────────────────

ENV_PATH        = Path(__file__).parent / "backend" / ".env"
BACKEND_DIR     = Path(__file__).parent / "backend"
FRONTEND_DIR    = Path(__file__).parent / "frontend"
NGROK_LOCAL_API = "http://localhost:4040/api/tunnels"
BACKEND_PORT    = 8000
FRONTEND_PORT   = 5173

# ── Colours ──────────────────────────────────────────────────────────────────

RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"

def ok(msg: str)   -> None: print(f"  {GREEN}✅ {msg}{RESET}")
def err(msg: str)  -> None: print(f"  {RED}❌ {msg}{RESET}")
def info(msg: str) -> None: print(f"  {BLUE}ℹ  {msg}{RESET}")
def warn(msg: str) -> None: print(f"  {YELLOW}⚠  {msg}{RESET}")
def step(n: int, total: int, msg: str) -> None:
    print(f"\n{BOLD}[{n}/{total}] {msg}{RESET}")

# ── Banner ────────────────────────────────────────────────────────────────────

BANNER = f"""
{RED}{BOLD}  ██╗  ██╗███████╗██╗     ██╗██╗  ██╗
  ██║  ██║██╔════╝██║     ██║╚██╗██╔╝
  ███████║█████╗  ██║     ██║ ╚███╔╝
  ██╔══██║██╔══╝  ██║     ██║ ██╔██╗
  ██║  ██║███████╗███████╗██║██╔╝ ██╗
  ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝{RESET}
{DIM}  Autonomous CI/CD Healing Agent{RESET}
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_env(key: str, value: str) -> None:
    """Write a key=value pair to backend/.env, creating the file if needed."""
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.touch(exist_ok=True)
    set_key(str(ENV_PATH), key, value)


def _read_env(key: str) -> str:
    """Read a value from backend/.env."""
    load_dotenv(str(ENV_PATH))
    return os.getenv(key, "")


def _prompt(msg: str, secret: bool = False, default: str = "") -> str:
    """Prompt user for input, with optional default."""
    default_hint = f" [{default}]" if default else ""
    try:
        if secret:
            import getpass
            value = getpass.getpass(f"  {BOLD}{msg}{default_hint}: {RESET}")
        else:
            value = input(f"  {BOLD}{msg}{default_hint}: {RESET}").strip()
        return value or default
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(0)


def _get_ngrok_url(retries: int = 10, delay: float = 1.0) -> str | None:
    """Poll ngrok's local API until a tunnel is available."""
    for _ in range(retries):
        try:
            resp = requests.get(NGROK_LOCAL_API, timeout=3)
            tunnels = resp.json().get("tunnels", [])
            for t in tunnels:
                if t.get("proto") == "https":
                    return t["public_url"]
        except Exception:
            pass
        time.sleep(delay)
    return None


def _check_command(cmd: str) -> bool:
    """Return True if a shell command is available on PATH."""
    try:
        subprocess.run(
            [cmd, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _stream_output(proc: subprocess.Popen, prefix: str = "") -> None:
    """Stream subprocess stdout to terminal in a daemon thread."""
    def _read():
        for line in iter(proc.stdout.readline, b""):
            print(f"{DIM}{prefix}{line.decode(errors='ignore').rstrip()}{RESET}")
    t = threading.Thread(target=_read, daemon=True)
    t.start()


# ── Setup Steps ───────────────────────────────────────────────────────────────

def _step_github_token() -> tuple[str, str]:
    """Collect and validate GitHub token + repo."""
    step(1, 5, "GitHub credentials")
    info("Create a token at: https://github.com/settings/tokens")
    info("Required scopes: repo, workflow")
    print()

    existing_token = _read_env("GITHUB_TOKEN")
    token = _prompt("GitHub personal access token", secret=True, default=existing_token)

    # Validate token
    try:
        g = Github(token)
        user = g.get_user()
        ok(f"Authenticated as {BOLD}{user.login}{RESET}")
    except GithubException:
        err("Invalid token — please check and try again.")
        sys.exit(1)

    existing_repo = _read_env("GITHUB_REPO")
    repo_name = _prompt("Repository to watch (e.g. org/repo)", default=existing_repo)

    # Validate repo exists
    try:
        g.get_repo(repo_name)
        ok(f"Repository {BOLD}{repo_name}{RESET} found")
    except GithubException:
        err(f"Repository '{repo_name}' not found or not accessible with this token.")
        sys.exit(1)

    _write_env("GITHUB_TOKEN", token)
    _write_env("GITHUB_REPO", repo_name)
    return token, repo_name


def _step_ai_key() -> None:
    """Collect AI API key."""
    step(2, 5, "AI API key")

    existing = _read_env("GEMINI_API_KEY") or _read_env("ANTHROPIC_API_KEY")
    if existing:
        info("API key already configured — skipping.")
        return

    print(f"  {DIM}Helix uses an LLM to diagnose failures and generate fixes.{RESET}")
    print(f"  {DIM}Supported: Gemini (free) or Anthropic Claude.{RESET}\n")

    choice = _prompt("Provider (gemini / anthropic)", default="gemini")

    if choice.lower() == "anthropic":
        info("Get a key at: https://console.anthropic.com")
        key = _prompt("Anthropic API key", secret=True)
        _write_env("ANTHROPIC_API_KEY", key)
        ok("Anthropic API key saved")
    else:
        info("Get a free key at: https://aistudio.google.com/apikey")
        key = _prompt("Gemini API key", secret=True)
        _write_env("GEMINI_API_KEY", key)
        ok("Gemini API key saved")


def _step_ngrok() -> str:
    """Start ngrok and return the public HTTPS URL."""
    step(3, 5, "Starting ngrok tunnel")

    if not _check_command("ngrok"):
        err("ngrok not found. Install from https://ngrok.com/download then re-run.")
        sys.exit(1)

    # Kill any existing ngrok process on port 4040
    try:
        requests.get(NGROK_LOCAL_API, timeout=1)
        info("ngrok already running — reusing existing tunnel.")
        url = _get_ngrok_url(retries=3, delay=0.5)
        if url:
            ok(f"Tunnel: {BOLD}{url}{RESET}")
            return url
    except Exception:
        pass

    # Start ngrok
    proc = subprocess.Popen(
        ["ngrok", "http", str(BACKEND_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print(f"  {DIM}Waiting for tunnel...{RESET}", end="", flush=True)
    url = _get_ngrok_url(retries=15, delay=1.0)

    if not url:
        print()
        err("Could not get ngrok URL. Is your authtoken configured?")
        err("Run: ngrok config add-authtoken YOUR_TOKEN")
        proc.terminate()
        sys.exit(1)

    print(f"\r  {GREEN}✅ Tunnel: {BOLD}{url}{RESET}          ")
    return url


def _step_webhook(token: str, repo_name: str, public_url: str) -> str:
    """Create GitHub webhook automatically."""
    step(4, 5, "Configuring GitHub webhook")

    webhook_secret = secrets.token_hex(16)
    webhook_url    = f"{public_url}/webhook/github"

    g    = Github(token)
    repo = g.get_repo(repo_name)

    # Remove any existing Helix webhooks
    for hook in repo.get_hooks():
        if "webhook/github" in hook.config.get("url", ""):
            hook.delete()
            info("Removed old Helix webhook.")

    # Create new webhook
    try:
        repo.create_hook(
            name="web",
            config={
                "url": webhook_url,
                "content_type": "json",
                "secret": webhook_secret,
            },
            events=["workflow_run", "workflow_job", "push"],
            active=True,
        )
        ok(f"Webhook created → {BOLD}{webhook_url}{RESET}")
    except GithubException as e:
        err(f"Could not create webhook: {e}")
        err("Make sure your token has the 'admin:repo_hook' scope.")
        sys.exit(1)

    _write_env("GITHUB_WEBHOOK_SECRET", webhook_secret)
    _write_env("WEBHOOK_URL", webhook_url)
    return webhook_secret


def _step_start_services() -> None:
    """Start the FastAPI backend and React frontend."""
    step(5, 5, "Starting Helix services")

    # ── Backend ──
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "0.0.0.0", "--port", str(BACKEND_PORT), "--reload"],
        cwd=str(BACKEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    _stream_output(backend_proc, prefix="  [backend] ")

    # Wait for backend to be ready
    print(f"  {DIM}Waiting for backend...{RESET}", end="", flush=True)
    for _ in range(20):
        try:
            r = requests.get(f"http://localhost:{BACKEND_PORT}/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    print(f"\r  {GREEN}✅ Backend running on http://localhost:{BACKEND_PORT}{RESET}    ")

    # ── Frontend ──
    if FRONTEND_DIR.exists() and _check_command("npm"):
        # Install deps if needed
        if not (FRONTEND_DIR / "node_modules").exists():
            info("Installing frontend dependencies (first run)...")
            subprocess.run(
                ["npm", "install"],
                cwd=str(FRONTEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(FRONTEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        _stream_output(frontend_proc, prefix="  [frontend] ")
        time.sleep(3)
        ok(f"Dashboard running on {BOLD}http://localhost:{FRONTEND_PORT}{RESET}")

        # Open browser automatically
        webbrowser.open(f"http://localhost:{FRONTEND_PORT}")
    else:
        warn("Frontend not found or npm not installed — skipping dashboard.")


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_init() -> None:
    """Full setup: credentials → ngrok → webhook → start services."""
    print(BANNER)
    print(f"{BOLD}  Setting up Helix on your machine...{RESET}\n")

    token, repo_name = _step_github_token()
    _step_ai_key()
    public_url       = _step_ngrok()
    _step_webhook(token, repo_name, public_url)
    _step_start_services()

    # ── Done ──
    print(f"""
{GREEN}{BOLD}
  ╔══════════════════════════════════════════════╗
  ║         Helix is live and watching!          ║
  ╚══════════════════════════════════════════════╝{RESET}

  {BOLD}Repo:{RESET}       {repo_name}
  {BOLD}Dashboard:{RESET}  http://localhost:{FRONTEND_PORT}
  {BOLD}Backend:{RESET}    http://localhost:{BACKEND_PORT}

  {DIM}Helix will automatically detect CI failures,
  diagnose them, generate fixes, and open PRs.

  Press CTRL+C to stop all services.{RESET}
""")

    # Keep alive — handle CTRL+C gracefully
    try:
        signal.pause()
    except (AttributeError, KeyboardInterrupt):
        # signal.pause() not available on Windows
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    print(f"\n{YELLOW}Shutting down Helix...{RESET}")
    sys.exit(0)


def cmd_status() -> None:
    """Check if Helix backend is running."""
    try:
        r = requests.get(f"http://localhost:{BACKEND_PORT}/health", timeout=3)
        data = r.json()
        ok(f"Helix backend is running — active runs: {data.get('active_runs', 0)}")
    except Exception:
        err("Helix backend is not running. Run: python cli.py init")


def cmd_stop() -> None:
    """Stop all Helix processes."""
    info("Stopping ngrok...")
    subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    info("Stopping uvicorn...")
    subprocess.run(["taskkill", "/F", "/IM", "uvicorn.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok("Helix stopped.")


def cmd_help() -> None:
    print(BANNER)
    print(f"""  {BOLD}Usage:{RESET}  python cli.py <command>

  {BOLD}Commands:{RESET}
    {GREEN}init{RESET}      Full setup — credentials, webhook, start services
    {GREEN}status{RESET}    Check if Helix backend is running
    {GREEN}stop{RESET}      Stop all Helix processes
    {GREEN}help{RESET}      Show this message
""")


# ── Entry point ───────────────────────────────────────────────────────────────

COMMANDS = {
    "init":   cmd_init,
    "status": cmd_status,
    "stop":   cmd_stop,
    "help":   cmd_help,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    handler = COMMANDS.get(cmd)
    if handler:
        handler()
    else:
        err(f"Unknown command: '{cmd}'")
        cmd_help()
        sys.exit(1)