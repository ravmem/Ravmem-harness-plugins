"""Tests for core/scripts/setup_stack.py using a fake `docker` and a mock RavMem server (no real stack)."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("setup_stack", ROOT / "core" / "scripts" / "setup_stack.py")
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)

COMPOSE = "services:\n  arcadedb:\n    image: arcadedata/arcadedb:1\n  ravmem:\n    image: ravmem/ravmem:latest\n"
KEY = "RAVMEM-TEST-AAAA-BBBB-CCCC"

FAKE_DOCKER = """#!/usr/bin/env python3
import os, sys
open(os.environ["FAKE_DOCKER_LOG"], "a").write(" ".join(sys.argv[1:]) + "\\n")
a = sys.argv[1:]
sys.exit(1 if a and a[0] == "inspect" else 0)
"""


class Mock(BaseHTTPRequestHandler):
    state = {}

    def log_message(self, *a):
        pass

    def _send(self, code, body="{}", ctype="application/json"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        st = self.state
        st.setdefault("seen", []).append(("GET", self.path, self.headers.get("Authorization"), self.headers.get("Cache-Control")))
        if self.path == "/compose.yml":
            return self._send(200, st.get("compose", COMPOSE), "text/yaml")
        if self.path == "/health":
            return self._send(200, '{"status":"ok"}')
        if self.path == "/api/license/status":
            if not st.get("sealed"):
                return self._send(404)
            return self._send(200, json.dumps({"status": "ACTIVE" if st.get("inited") else "NOT_INITIALIZED",
                                               "token_integrity": "ok", "expiry_ts": 1893456000,
                                               "key_hash_prefix": st.get("hash", "")[:12]}))
        self._send(404)

    def do_POST(self):
        st = self.state
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        st.setdefault("posts", []).append((self.path, body))
        if self.path == "/activate":
            if st.get("sealed"):
                return self._send(404)
            if st.get("reject"):
                return self._send(403, json.dumps({"detail": st["reject"]}))
            st["sealed"] = True
            return self._send(200)
        if self.path == "/api/license/init":
            if st.get("inited"):
                return self._send(409, '{"detail":"already"}')
            st["inited"], st["hash"] = True, body["key_hash"]
            return self._send(200, '{"status":"ACTIVE","expiry_ts":1893456000}')
        self._send(404)


class SetupStackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        docker = self.bin / "docker"
        docker.write_text(FAKE_DOCKER)
        docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
        self.log = self.tmp / "docker.log"
        self.server = HTTPServer(("127.0.0.1", 0), Mock)
        Mock.state = {}
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/compose.yml"
        self._env = dict(os.environ)
        os.environ.update(PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}", FAKE_DOCKER_LOG=str(self.log))
        os.environ.pop(ss.LICENSE_KEY_ENV, None)
        os.environ.pop(ss.COMPOSE_URL_ENV, None)
        self.home = self.tmp / "home"
        ss.HOME, ss.CLIENT_JSON = self.home, self.home / "client.json"
        self.stack = self.tmp / "stack"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        os.environ.clear()
        os.environ.update(self._env)

    def run_main(self, *extra, key=KEY):
        if key:
            os.environ[ss.LICENSE_KEY_ENV] = key
        argv = ["--dir", str(self.stack), "--compose-url", self.url, "--port", str(self.port), "--ui-port", "3999", "--wait", "10", *extra]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ss.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def docker_calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_full_install(self):
        rc, out, err = self.run_main()
        self.assertEqual(rc, 0, err)
        self.assertEqual((self.stack / "docker-compose.yml").read_text(), COMPOSE)
        env = ss.read_env(self.stack / ".env")
        self.assertTrue(env["RAVMEM_ADMIN_TOKEN"].startswith("rv_admin_"))
        self.assertEqual(env["RAVMEM_PORT"], str(self.port))
        self.assertEqual(oct((self.stack / ".env").stat().st_mode & 0o777), "0o600")
        client = json.loads(ss.CLIENT_JSON.read_text())
        self.assertEqual(client, {"server_url": f"http://localhost:{self.port}", "api_key": env["RAVMEM_ADMIN_TOKEN"]})
        calls = self.docker_calls()
        self.assertTrue(any(" pull" in c for c in calls) and any(" up -d" in c for c in calls), calls)
        init = [b for p, b in Mock.state["posts"] if p == "/api/license/init"][0]
        self.assertEqual(init["key_hash"], hashlib.sha256(KEY.encode()).hexdigest())
        # the key never reaches disk or stdout
        for f in (self.stack / ".env", ss.CLIENT_JSON):
            self.assertNotIn(KEY, f.read_text())
        self.assertNotIn(KEY, out + err)
        self.assertNotIn(env["RAVMEM_ADMIN_TOKEN"], out + err)

    def test_compose_fetched_fresh_with_no_cache_header(self):
        self.run_main()
        gets = [s for s in Mock.state["seen"] if s[1] == "/compose.yml"]
        self.assertEqual(gets[0][3], "no-cache")

    def test_compose_changes_are_picked_up_on_rerun(self):
        self.run_main()
        Mock.state["compose"] = COMPOSE + "  ravmem-ui:\n    image: ravmem/ravmem-ui:latest\n"
        rc, *_ = self.run_main(key=None)
        self.assertEqual(rc, 0)
        self.assertIn("ravmem-ui", (self.stack / "docker-compose.yml").read_text())

    def test_rerun_is_idempotent_and_needs_no_key(self):
        self.run_main()
        secrets1 = ss.read_env(self.stack / ".env")
        rc, out, err = self.run_main(key=None)
        self.assertEqual(rc, 0, err)
        self.assertIn("already active", out)
        self.assertEqual(ss.read_env(self.stack / ".env"), secrets1)

    def test_bad_compose_status_stops_before_docker(self):
        self.url = f"http://127.0.0.1:{self.port}/missing.yml"
        rc, _, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("404", err)
        self.assertFalse(any(" up" in c for c in self.docker_calls()))

    def test_wrong_content_rejected(self):
        Mock.state["compose"] = "<html>not yaml</html>"
        rc, _, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("did not return a RavMem compose file", err)

    def test_insecure_remote_url_refused(self):
        with self.assertRaises(ss.SetupError):
            ss.fetch_compose("http://example.com/docker-compose.yml")

    def test_no_terminal_and_no_env_key_fails_with_guidance(self):
        rc, _, err = self.run_main(key=None)
        self.assertEqual(rc, 1)
        self.assertIn("RAVMEM_LICENSE_KEY", err)

    def test_license_refusal_has_hint(self):
        Mock.state["reject"] = "LICENSE_REVOKED"
        rc, _, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("revoked", err.lower())

    def test_existing_client_json_for_other_server_not_overwritten(self):
        self.home.mkdir(parents=True)
        ss.CLIENT_JSON.write_text(json.dumps({"server_url": "http://other:7432", "api_key": "x", "default_project": "p"}))
        rc, out, _ = self.run_main()
        self.assertEqual(rc, 0)
        self.assertIn("skipped", out)
        self.assertEqual(json.loads(ss.CLIENT_JSON.read_text())["server_url"], "http://other:7432")

    def test_yes_replaces_client_json_keeps_other_keys_and_backs_up(self):
        self.home.mkdir(parents=True)
        ss.CLIENT_JSON.write_text(json.dumps({"server_url": "http://other:7432", "api_key": "x", "default_project": "p"}))
        rc, *_ = self.run_main("--yes")
        self.assertEqual(rc, 0)
        data = json.loads(ss.CLIENT_JSON.read_text())
        self.assertEqual(data["server_url"], f"http://localhost:{self.port}")
        self.assertEqual(data["default_project"], "p")
        self.assertTrue(ss.CLIENT_JSON.with_suffix(".json.bak").exists())


if __name__ == "__main__":
    unittest.main()
