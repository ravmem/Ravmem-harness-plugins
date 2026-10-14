#!/usr/bin/env python3
"""Install and activate the RavMem server stack with Docker Compose.

Steps: check Docker, fetch the *latest* compose file from the RavMem docs (never a bundled copy),
create secrets in a private .env, pull images, start the stack, wait for it to be healthy, activate the
license, write ~/.ravmem/client.json so every RavMem plugin and the CLI can connect, and optionally install ravmem-cli.

The license key is typed into the terminal (hidden) or read from RAVMEM_LICENSE_KEY. It is never taken
from the command line, so it does not end up in shell history, process lists or a chat transcript.

Standard library only: this file is copied into every harness plugin directory.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

COMPOSE_URL = "https://ravmem.com/docs/docker-compose.yml"
COMPOSE_URL_ENV = "RAVMEM_COMPOSE_URL"
LICENSE_KEY_ENV = "RAVMEM_LICENSE_KEY"
PROJECT = "ravmem"
DEFAULT_PORT = 7432
DEFAULT_UI_PORT = 3000
HOME = Path.home() / ".ravmem"
CLIENT_JSON = HOME / "client.json"
DEFAULT_DIR = HOME / "stack"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class SetupError(RuntimeError):
    """A failure with a message that is safe and useful to show the user."""


def say(msg: str = "") -> None:
    print(msg, flush=True)


# --- docker ----------------------------------------------------------------------------------------

def docker(*args: str, cwd: Path | None = None, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(
            ["docker", *args], cwd=cwd, text=True, check=False,
            stdout=subprocess.PIPE if capture else None, stderr=subprocess.STDOUT if capture else None,
        )
    except FileNotFoundError:
        raise SetupError("Docker is not installed. Install Docker Desktop (Windows/macOS) or Docker Engine "
                         "(Linux): https://docs.docker.com/get-docker/ then run this again.")
    if check and proc.returncode != 0:
        tail = (proc.stdout or "").strip().splitlines()[-8:]
        raise SetupError(f"`docker {' '.join(args[:3])}` failed:\n  " + "\n  ".join(tail))
    return proc


def check_docker() -> None:
    if not shutil.which("docker"):
        docker("version")  # raises the install hint
    if docker("compose", "version", check=False).returncode != 0:
        raise SetupError("Docker Compose v2 is required (`docker compose`). Update Docker: https://docs.docker.com/compose/install/")
    if docker("info", check=False).returncode != 0:
        raise SetupError("The Docker daemon is not running. Start Docker Desktop (or `sudo systemctl start docker`) and try again.")


def foreign_container(directory: Path) -> str | None:
    """Name of an existing container the stack needs that was not created by this stack directory."""
    for name in ("ravmem", "arcadedb", "ravmem-ui"):
        out = docker("inspect", "-f", '{{index .Config.Labels "com.docker.compose.project.working_dir"}}', name, check=False)
        if out.returncode != 0:
            continue  # no such container
        if Path(out.stdout.strip() or "/nonexistent").resolve() != directory.resolve():
            return name
    return None


# --- compose file ----------------------------------------------------------------------------------

def fetch_compose(url: str, allow_insecure: bool = False) -> str:
    """Download the compose file fresh. Raises rather than falling back to anything stale."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" and not (parts.hostname in LOCAL_HOSTS or allow_insecure):
        raise SetupError(f"Refusing to fetch the compose file over {parts.scheme or 'an unknown scheme'}: use an https URL.")
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "Pragma": "no-cache", "User-Agent": "ravmem-setup"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read(1_000_000).decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise SetupError(f"Could not download the compose file ({exc.code}) from {url}")
    except (urllib.error.URLError, OSError, UnicodeDecodeError) as exc:
        raise SetupError(f"Could not download the compose file from {url}: {exc}")
    if not re.search(r"^services:\s*$", body, re.M) or not re.search(r"^\s+ravmem:\s*$", body, re.M):
        raise SetupError(f"{url} did not return a RavMem compose file (no `services:` / `ravmem:` service).")
    return body


def images_in(compose: str) -> list[str]:
    return re.findall(r"^\s+image:\s*(\S+)", compose, re.M)


# --- env file --------------------------------------------------------------------------------------

def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip()
    return values


def write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass  # e.g. Windows


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def pick_port(preferred: int) -> int:
    for port in range(preferred, preferred + 50):
        if port_free(port):
            return port
    raise SetupError(f"No free port found from {preferred} to {preferred + 49}; pass --port / --ui-port.")


def ensure_env(path: Path, port: int | None, ui_port: int | None, stack_running: bool) -> dict[str, str]:
    """Create .env with fresh secrets once; on re-runs keep the existing secrets (ArcadeDB's password is
    fixed at first start) and only add what is missing."""
    env = read_env(path)
    env.setdefault("ARCADEDB_PASSWORD", secrets.token_urlsafe(24))
    env.setdefault("RAVMEM_ADMIN_TOKEN", "rv_admin_" + secrets.token_urlsafe(32))
    if port:
        env["RAVMEM_PORT"] = str(port)
    elif "RAVMEM_PORT" not in env:
        env["RAVMEM_PORT"] = str(DEFAULT_PORT if stack_running else pick_port(DEFAULT_PORT))
    if ui_port:
        env["RAVMEM_UI_PORT"] = str(ui_port)
    elif "RAVMEM_UI_PORT" not in env:
        env["RAVMEM_UI_PORT"] = str(DEFAULT_UI_PORT if stack_running else pick_port(DEFAULT_UI_PORT))
    write_private(path, "# Generated by the RavMem setup script. Contains secrets: do not commit.\n"
                  + "".join(f"{k}={v}\n" for k, v in env.items()))
    return env


# --- server calls ----------------------------------------------------------------------------------

def call(base: str, method: str, path: str, token: str, body: dict | None = None, timeout: float = 30) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw, code = resp.read().decode() or "{}", resp.status
    except urllib.error.HTTPError as exc:
        raw, code = exc.read().decode() or "{}", exc.code
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"detail": raw[:200]}
    return code, parsed if isinstance(parsed, dict) else {"detail": parsed}


def wait_for(predicate, seconds: int, what: str, every: float = 2.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if predicate():
                return
        except (urllib.error.URLError, OSError, TimeoutError, ValueError):
            pass
        time.sleep(every)
    raise SetupError(f"Timed out after {seconds}s waiting for {what}. Check: docker compose -p {PROJECT} logs ravmem")


def healthy(base: str) -> bool:
    with urllib.request.urlopen(base + "/health", timeout=3) as resp:
        return resp.status == 200


def license_hint(detail: str) -> str:
    table = {
        "LICENSE_KEY_NOT_FOUND": "The license server does not recognise this key. Check it in the RavMem console.",
        "LICENSE_REVOKED": "This license was revoked. Rotate the key in the console and run this again with the new key.",
        "ACTIVATION_LIMIT_REACHED": "Every seat on this license is in use. Deactivate the old machine in the console, then retry.",
        "SUBSCRIPTION_SUSPENDED": "The subscription is suspended. Resolve billing in the console.",
        "SUBSCRIPTION_EXPIRED": "The subscription has expired. Renew it in the console.",
    }
    return next((v for k, v in table.items() if k in detail), "")


def activate_license(base: str, token: str, key: str, wait: int) -> dict:
    """Same sequence as `ravmem license activate`: seal the key to this machine, wait for the full server,
    then fetch the entitlements. Safe to repeat: an already-activated server answers 409/404."""
    key = key.strip()
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    code, body = call(base, "POST", "/activate", token, {"license_key": key})
    sealed_now = code < 300
    if code not in (404, 405) and code >= 300:
        detail = str(body.get("detail", body))
        raise SetupError(f"Activation failed ({code}): {detail}" + (f"\n  -> {license_hint(detail)}" if license_hint(detail) else ""))

    if sealed_now:
        say("  License sealed to this machine, waiting for the server to finish loading...")
        def full_server_up() -> bool:
            code, body = call(base, "GET", "/api/license/status", token)
            return code == 200 and body.get("status") not in (None, "ACTIVATION_REQUIRED")

        wait_for(full_server_up, wait, "the server to come up after activation")

    code, body = call(base, "POST", "/api/license/init", token, {"key_hash": key_hash, "license_key": key})
    if code == 409:
        status = call(base, "GET", "/api/license/status", token)[1]
        stored = status.get("key_hash_prefix")
        if status.get("status") in ("ACTIVE", "GRACE_PERIOD") and status.get("token_integrity") == "ok" \
                and not (stored and not key_hash.startswith(stored)):
            return status
        raise SetupError("This server already holds a different or unhealthy license. Run `ravmem license activate` "
                         "(pip install ravmem-cli) to repair or switch it.")
    if code >= 300:
        detail = str(body.get("detail", body))
        raise SetupError(f"Entitlement activation failed ({code}): {detail}" + (f"\n  -> {license_hint(detail)}" if license_hint(detail) else ""))
    return body


def read_license_key() -> str:
    key = (os.environ.get(LICENSE_KEY_ENV) or "").strip()
    if key:
        return key
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise SetupError(
            "No terminal to type the license key into. Run this in a terminal yourself (in Claude Code: type `! python3 "
            "<path-to>/setup_stack.py`), or export RAVMEM_LICENSE_KEY first. The key is never accepted as a command-line argument.")
    key = getpass.getpass("RavMem license key (input hidden): ").strip()
    if not key:
        raise SetupError("A license key is required.")
    return key


# --- client.json -----------------------------------------------------------------------------------

def write_client_json(server_url: str, token: str, assume_yes: bool) -> str:
    """Point the CLI and plugins at this server. Never silently redirect an existing, different setup."""
    current: dict = {}
    if CLIENT_JSON.exists():
        try:
            current = json.loads(CLIENT_JSON.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = {}
    same = current.get("server_url", "").rstrip("/") == server_url and current.get("api_key") == token
    if same:
        return "unchanged"
    if current.get("server_url") and current.get("server_url", "").rstrip("/") != server_url:
        if not assume_yes:
            if not sys.stdin.isatty():
                return f"skipped (existing {CLIENT_JSON} points to {current['server_url']}; re-run with --yes to replace it)"
            if input(f"{CLIENT_JSON} currently points to {current['server_url']}. Replace it? [y/N] ").strip().lower() != "y":
                return "skipped (kept the existing file)"
        shutil.copy2(CLIENT_JSON, CLIENT_JSON.with_suffix(".json.bak"))
    current.update({"server_url": server_url, "api_key": token})
    write_private(CLIENT_JSON, json.dumps(current, indent=2) + "\n")
    return "written"


# --- CLI -------------------------------------------------------------------------------------------

CLI_PACKAGE = "ravmem-cli"


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def install_cli(mode: str) -> str:
    """Install ravmem-cli (needed to index repositories). mode: ask | yes | no. Never fatal."""
    if shutil.which("ravmem"):
        return "already installed"
    if mode == "no":
        return f"skipped (install later with: pipx install {CLI_PACKAGE})"
    if mode == "ask":
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            return f"skipped (no terminal to ask; re-run with --cli or: pipx install {CLI_PACKAGE})"
        if input(f"Install the RavMem CLI ({CLI_PACKAGE}) so you can index repositories? [Y/n] ").strip().lower() not in ("", "y", "yes"):
            return "skipped"
    cmd = ["pipx", "install", CLI_PACKAGE] if shutil.which("pipx") else [sys.executable, "-m", "pip", "install", "--user", CLI_PACKAGE]
    proc = run_cmd(cmd)
    if proc.returncode != 0:
        tail = " | ".join((proc.stdout or "").strip().splitlines()[-2:])
        return f"failed ({tail}). Install it yourself: pipx install {CLI_PACKAGE}"
    note = "" if shutil.which("ravmem") else " (open a new terminal if `ravmem` is not found: its folder may not be on PATH yet)"
    return "installed" + note


# --- main ------------------------------------------------------------------------------------------

def install(args: argparse.Namespace) -> int:
    directory = Path(args.dir).expanduser()
    compose_path, env_path = directory / "docker-compose.yml", directory / ".env"

    say("1/7 Checking Docker")
    check_docker()
    clash = foreign_container(directory)
    if clash:
        raise SetupError(f"A container named '{clash}' already exists and was not created by this stack ({directory}). "
                         "Stop or remove it (or use --dir pointing at its compose directory) and try again.")

    url = args.compose_url or os.environ.get(COMPOSE_URL_ENV) or COMPOSE_URL
    say(f"2/7 Fetching the latest compose file\n  {url}")
    compose = fetch_compose(url, args.insecure)
    directory.mkdir(parents=True, exist_ok=True)
    compose_path.write_text(compose, encoding="utf-8")  # overwritten on every run: nothing is reused from a previous download
    say("  images: " + ", ".join(images_in(compose)))

    running = "ravmem" in (docker("compose", "-p", PROJECT, "-f", str(compose_path), "ps", "--status", "running", "--services",
                                  cwd=directory, check=False).stdout or "").split()
    env = ensure_env(env_path, args.port, args.ui_port, running)
    port, ui_port = env["RAVMEM_PORT"], env["RAVMEM_UI_PORT"]
    base = f"http://localhost:{port}"
    say(f"3/7 Starting the stack in {directory}\n  server :{port}   dashboard :{ui_port}")
    compose_cmd = ["compose", "-p", PROJECT, "--env-file", str(env_path), "-f", str(compose_path)]
    docker(*compose_cmd, "pull", cwd=directory)
    docker(*compose_cmd, "up", "-d", cwd=directory)

    say("4/7 Waiting for the server")
    wait_for(lambda: healthy(base), args.wait, "the server to answer /health")
    token = env["RAVMEM_ADMIN_TOKEN"]

    say("5/7 License")
    code, status = call(base, "GET", "/api/license/status", token)
    if code == 200 and status.get("status") in ("ACTIVE", "GRACE_PERIOD") and status.get("token_integrity", "ok") == "ok":
        say(f"  already active ({status.get('status')}), nothing to do")
    else:
        result = activate_license(base, token, read_license_key(), args.wait)
        say(f"  activated: {result.get('status')}  expires {result.get('expiry_ts')}")

    say("6/7 Connecting plugins")
    say(f"  {CLIENT_JSON}: {write_client_json(base, token, args.yes)}")
    say("7/7 RavMem CLI")
    say(f"  {install_cli('yes' if args.cli else 'no' if args.no_cli else 'ask')}")
    say("")
    say(f"RavMem is running.\n  API / MCP : {base}   (MCP at {base}/mcp)\n  Dashboard : http://localhost:{ui_port}\n"
        f"  Admin token is stored in {env_path} (and {CLIENT_JSON}); it is not printed here.\n"
        f"  Index a repo (from its root):  ravmem remote add . --name <project>  then  ravmem analyze . --project <project> --wait\n"
        f"  Stop: docker compose -p {PROJECT} -f {compose_path} down      (add -v only to delete all data)")
    return 0


def status(args: argparse.Namespace) -> int:
    directory = Path(args.dir).expanduser()
    env = read_env(directory / ".env")
    if not env:
        say(f"No stack found in {directory}. Run without arguments to install it.")
        return 1
    base = f"http://localhost:{env.get('RAVMEM_PORT', DEFAULT_PORT)}"
    try:
        healthy(base)
    except (urllib.error.URLError, OSError):
        say(f"Server at {base} is not answering. Start it: docker compose -p {PROJECT} -f {directory / 'docker-compose.yml'} up -d")
        return 1
    code, lic = call(base, "GET", "/api/license/status", env.get("RAVMEM_ADMIN_TOKEN", ""))
    say(f"Server {base}: up. License: {lic.get('status', code)}  expires {lic.get('expiry_ts', '?')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install and activate the RavMem server with Docker Compose.")
    parser.add_argument("command", nargs="?", choices=["install", "status"], default="install")
    parser.add_argument("--dir", default=str(DEFAULT_DIR), help=f"stack directory (default {DEFAULT_DIR})")
    parser.add_argument("--compose-url", help=f"compose file URL (default ${COMPOSE_URL_ENV} or {COMPOSE_URL})")
    parser.add_argument("--insecure", action="store_true", help="allow a non-https, non-localhost compose URL")
    parser.add_argument("--port", type=int, help=f"host port for the server (default {DEFAULT_PORT}, or the next free one)")
    parser.add_argument("--ui-port", type=int, help=f"host port for the dashboard (default {DEFAULT_UI_PORT}, or the next free one)")
    parser.add_argument("--wait", type=int, default=240, help="seconds to wait for the server (default 240)")
    parser.add_argument("--cli", action="store_true", help="install ravmem-cli without asking")
    parser.add_argument("--no-cli", action="store_true", help="do not install ravmem-cli")
    parser.add_argument("--yes", "-y", action="store_true", help="replace an existing ~/.ravmem/client.json without asking")
    args = parser.parse_args(argv)
    try:
        return status(args) if args.command == "status" else install(args)
    except SetupError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
