"""Serves the board locally and lets the page trigger a run on this machine.

    python -m src.serve            # http://127.0.0.1:8765
    python -m src.serve --port N   # somewhere else
    python -m src.serve --no-open  # do not open a browser

The published board on GitHub Pages is a static page and stays that way. This
serves the same docs/ folder from here, and adds three endpoints the page uses
when — and only when — it was loaded through this server:

    GET  /api/status    what the last or current run is doing
    POST /api/run       start one (mode: full | dry | urls)
    POST /api/stop      cancel the one in progress

The work itself is still run.ps1, so a button press and a terminal command do
exactly the same thing, including the pull-before and push-after.

It binds to the loopback address only: nothing outside this machine can reach
it. That is the whole of the access control, which is why it must stay
loopback — a run pushes commits and sends messages.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import threading
import webbrowser
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# The switches run.ps1 already understands; the page may pick a mode, not
# assemble a command line.
MODES = {
    "full": [],
    "dry": ["-DryRun"],
    "urls": ["-CheckUrls"],
    "nopush": ["-NoPush"],
}

MAX_LINES = 500  # a run prints a few dozen; this is only a runaway guard


class Runner:
    """One run at a time, its output kept in memory for the page to poll."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.proc: subprocess.Popen | None = None
        self.lines: list[str] = []
        self.mode = ""
        self.started = ""
        self.finished = ""
        self.exit_code: int | None = None
        self.seq = 0  # bumps on each start, so a stale poll can tell

    # -- state the page reads ---------------------------------------------
    def status(self, since: int = 0) -> dict:
        with self.lock:
            running = self.proc is not None and self.proc.poll() is None
            return {
                "running": running,
                "mode": self.mode,
                "started": self.started,
                "finished": self.finished,
                "exit_code": self.exit_code,
                "seq": self.seq,
                "total": len(self.lines),
                "lines": self.lines[since:],
            }

    # -- starting and stopping --------------------------------------------
    def start(self, mode: str) -> tuple[bool, str]:
        if mode not in MODES:
            return False, f"unknown mode {mode!r}"
        with self.lock:
            if self.proc is not None and self.proc.poll() is None:
                return False, "a run is already in progress"
            shell = _powershell()
            if not shell:
                return False, "PowerShell not found on PATH"
            cmd = [shell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                   "-File", str(ROOT / "run.ps1"), *MODES[mode]]
            self.lines = []
            self.mode = mode
            self.started = datetime.now().strftime("%H:%M:%S")
            self.finished = ""
            self.exit_code = None
            self.seq += 1
            # Writing to a pipe rather than a console makes Python buffer in
            # 8 KB blocks, so the whole run's output would arrive at the end
            # and the page would show an empty log throughout.
            env = {**os.environ, "PYTHONUNBUFFERED": "1"}
            # Started from the Startup entry there is no console to inherit,
            # so PowerShell would allocate one of its own and a black window
            # would appear over whatever you were doing, mid-run.
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            self.proc = subprocess.Popen(
                cmd, cwd=str(ROOT), env=env, creationflags=flags,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace",
                bufsize=1,
            )
            proc = self.proc
        threading.Thread(target=self._drain, args=(proc,), daemon=True).start()
        return True, "started"

    def stop(self) -> tuple[bool, str]:
        with self.lock:
            proc = self.proc
            if proc is None or proc.poll() is not None:
                return False, "nothing running"
        # PowerShell is only the wrapper: terminating it leaves python -m
        # src.main running, still holding the pipe, so the run would carry on
        # invisibly. The whole tree has to go.
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True)
        else:
            proc.terminate()
        return True, "stopping"

    def _drain(self, proc: subprocess.Popen) -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            with self.lock:
                if proc is not self.proc:  # superseded; drop it
                    return
                self.lines.append(line.rstrip("\r\n"))
                if len(self.lines) > MAX_LINES:
                    del self.lines[:-MAX_LINES]
        code = proc.wait()
        with self.lock:
            if proc is self.proc:
                self.exit_code = code
                self.finished = datetime.now().strftime("%H:%M:%S")


def _powershell() -> str | None:
    return shutil.which("pwsh") or shutil.which("powershell")


class Handler(SimpleHTTPRequestHandler):
    """docs/ as a site, plus the three control endpoints."""

    runner: Runner

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DOCS), **kw)

    # The board is rewritten under the browser's feet; a cached copy would
    # show yesterday's page after a refresh that plainly said it succeeded.
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):  # the page polls; the log would scroll
        return

    def _json(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _local(self) -> bool:
        """A page on some other site could POST here from the user's browser;
        the address it came from is the only thing distinguishing that from
        our own page, so a run refuses to start without it."""
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        origin = self.headers.get("Origin")
        if host not in ("127.0.0.1", "localhost", "[::1]"):
            return False
        if origin is not None:
            allowed = {f"http://127.0.0.1:{self.server.server_address[1]}",
                       f"http://localhost:{self.server.server_address[1]}"}
            if origin not in allowed:
                return False
        return True

    def do_GET(self):
        if self.path.startswith("/api/status"):
            since = 0
            _, _, query = self.path.partition("?")
            for part in query.split("&"):
                key, _, val = part.partition("=")
                if key == "since" and val.isdigit():
                    since = int(val)
            return self._json(self.runner.status(since))
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path not in ("/api/run", "/api/stop"):
            return self._json({"error": "not found"}, 404)
        if not self._local():
            return self._json({"error": "local requests only"}, 403)

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            payload = {}

        if path == "/api/stop":
            ok, msg = self.runner.stop()
        else:
            ok, msg = self.runner.start(str(payload.get("mode", "full")))
        return self._json({"ok": ok, "message": msg,
                           **self.runner.status()}, 200 if ok else 409)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true",
                    help="do not open a browser window")
    args = ap.parse_args()

    if not (DOCS / "index.html").exists():
        print("docs/index.html is not there yet — run .\\run.ps1 once first.")
        return 1

    runner = Runner()
    handler = type("BoundHandler", (Handler,), {"runner": runner})
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Board at {url}   (Ctrl+C to stop)")
    print("The Refresh button on the page runs run.ps1 here.")
    if not args.no_open:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
