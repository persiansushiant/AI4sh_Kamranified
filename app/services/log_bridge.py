"""Local notebook-to-runtime logging; standard library only.

One UI runtime per project checkout. Both processes must use this same checkout
and OS account. A notebook re-reads discovery on every message, so opening or
closing the UI during execution is supported.
"""
import atexit
import hashlib
import hmac
import http.client
import json
import os
from pathlib import Path
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _discovery_file():
    project = str(Path(__file__).resolve().parents[2])
    key = hashlib.sha256(os.path.normcase(project).encode()).hexdigest()[:24]
    return Path.home() / ".ai4sh" / "log_bridge" / (key + ".json")


def _request(endpoint, payload=None):
    port = endpoint["port"]
    token = endpoint["token"]
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Invalid bridge port")
    if not isinstance(token, str):
        raise ValueError("Invalid bridge token")
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)
    try:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        connection.request(
            "GET" if payload is None else "POST",
            "/health" if payload is None else "/log",
            body=body,
            headers={"Authorization": "Bearer " + token,
                     "Content-Type": "application/json"},
        )
        response = connection.getresponse()
        response.read()
        return response.status == 204
    finally:
        connection.close()


def _endpoint():
    return json.loads(_discovery_file().read_text(encoding="utf-8"))


class NotebookServices:
    """Only log is available outside a bound workspace context."""

    def log(self, message, section="process", status="info"):
        payload = dict(message=str(message), section=str(section), status=str(status))
        try:
            if _request(_endpoint(), payload):
                return
        except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
            pass
        print(f"[{section}] [{status}] {message}", flush=True)

    def __getattr__(self, name):
        raise RuntimeError(
            f"Workspace service '{name}' requires a bound UI runtime; "
            "only log() is available in standalone execution"
        )


notebook_services = NotebookServices()


class LogBridge:
    def __init__(self, runtime):
        discovery = _discovery_file()
        try:
            existing = _endpoint()
            alive = _request(existing)
        except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
            alive = False
        if alive:
            raise RuntimeError("A UI log receiver is already running for this project")

        token = secrets.token_urlsafe(32)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _authorized(self):
                provided = self.headers.get("Authorization", "")
                return hmac.compare_digest(provided.encode(), ("Bearer " + token).encode())

            def _reply(self, status):
                self.send_response(status)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_GET(self):
                self._reply(204 if self._authorized() and self.path == "/health" else 404)

            def do_POST(self):
                self.connection.settimeout(1)
                if not self._authorized() or self.path != "/log":
                    self._reply(403)
                    return
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 1024 * 1024:
                        raise ValueError("Invalid message size")
                    payload = json.loads(self.rfile.read(size))
                    if not isinstance(payload, dict) or set(payload) != {"message", "section", "status"}:
                        raise ValueError("Invalid fields")
                    if not all(isinstance(value, str) for value in payload.values()):
                        raise ValueError("Invalid values")
                    # Runtime.log validates section/status and holds its own lock.
                    runtime.log(**payload)
                except (ValueError, TypeError, OSError):
                    self._reply(400)
                    return
                except Exception:
                    self._reply(500)
                    return
                self._reply(204)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._closed = False
        self._token = token
        self._discovery = discovery
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        try:
            discovery.parent.mkdir(parents=True, exist_ok=True)
            temporary = discovery.with_name(discovery.name + "." + token + ".tmp")
            try:
                with open(temporary, "x", encoding="utf-8") as file:
                    os.chmod(temporary, 0o600)
                    json.dump(dict(port=self._server.server_port, token=token), file)
                os.replace(temporary, discovery)
            finally:
                temporary.unlink(missing_ok=True)
        except Exception:
            self.close()
            raise
        atexit.register(self.close)

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
        try:
            if _endpoint().get("token") == self._token:
                self._discovery.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError):
            pass
