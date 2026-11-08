"""Dashboard HTTP API: host/origin/header checks, path confinement, read endpoints, static page."""
import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from harness.monitor import asciify
from harness.monitor.server import LOOPBACK, make_handler
from harness.pipeline import job as job_module
from harness.pipeline.job import Job
from harness.utils import ffmpeg, run_command


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.jobs = Path(cls.temp.name) / "jobs"
        cls.patch = patch.object(job_module, "JOBS_DIR", cls.jobs)
        cls.patch.start()
        video = Path(cls.temp.name) / "v.mp4"
        run_command([ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=red:s=64x36:r=10:d=2",
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)])
        cls.job = Job.create("demo-job", video, title="Demo")
        (cls.job.root / "01_probe" / "note.txt").write_text("xin chào", encoding="utf-8")
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(set(LOOPBACK)))
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.patch.stop()
        cls.temp.cleanup()

    def request(self, method, path, body=None, headers=None, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = {"Host": host or f"127.0.0.1:{self.port}", **(headers or {})}
        data = json.dumps(body).encode() if body is not None else None
        conn.request(method, path, body=data, headers=hdrs)
        response = conn.getresponse()
        payload = response.read()
        conn.close()
        return response.status, dict(response.getheaders()), payload

    def post(self, path, body, **extra):
        headers = {"Content-Type": "application/json", "X-Harness": "1", **extra}
        return self.request("POST", path, body, headers)

    def test_page_is_ascii_and_sent_with_csp(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        body.decode("ascii")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(asciify.main(["--check"]), 0, "run python -m harness.monitor.asciify")

    def test_overview_and_detail(self):
        status, headers, body = self.request("GET", "/api/overview")
        self.assertEqual(status, 200)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        data = json.loads(body)
        self.assertEqual([j["job"] for j in data["jobs"]], ["demo-job"])
        status, _, body = self.request("GET", "/api/jobs/demo-job")
        detail = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual([s["id"] for s in detail["stages"]], ["probe", "read", "write", "measure", "render", "qc"])
        self.assertEqual(self.request("GET", "/api/jobs/nope")[0], 404)
        self.assertEqual(self.request("GET", "/api/jobs/..%2F..%2Fetc")[0], 400)

    def test_foreign_host_is_refused(self):
        self.assertEqual(self.request("GET", "/api/overview", host="evil.example:80")[0], 421)

    def test_writes_need_header_json_and_same_origin(self):
        body = {"stage": "read", "approved": True}
        self.assertEqual(self.request("POST", "/api/jobs/demo-job/gate", body, {"Content-Type": "application/json"})[0], 403)
        self.assertEqual(self.request("POST", "/api/jobs/demo-job/gate", body, {"X-Harness": "1", "Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.post("/api/jobs/demo-job/gate", body, Origin="https://evil.example")[0], 403)
        status, _, payload = self.post("/api/jobs/demo-job/gate", body, Origin=f"http://127.0.0.1:{self.port}")
        self.assertEqual(status, 400)          # allowed through, refused because READ has no output yet
        self.assertIn("approve", json.loads(payload)["error"])

    def test_file_serving_is_confined_and_supports_ranges(self):
        status, headers, body = self.request("GET", "/api/jobs/demo-job/file?path=01_probe/note.txt")
        self.assertEqual((status, body.decode()), (200, "xin chào"))
        self.assertIn("charset=utf-8", headers["Content-Type"])
        status, headers, body = self.request("GET", "/api/jobs/demo-job/file?path=01_probe/note.txt", headers={"Range": "bytes=0-2"})
        self.assertEqual((status, body, headers["Content-Range"]), (206, b"xin", f"bytes 0-2/{len('xin chào'.encode())}"))
        for bad in ("../../etc/passwd", "/etc/passwd", "01_probe/../../demo-job/../x", ".state.lock"):
            self.assertIn(self.request("GET", f"/api/jobs/demo-job/file?path={bad}")[0], (400, 403, 404), bad)
        status, headers, _ = self.request("GET", "/api/jobs/demo-job/file?path=source", headers={"Range": "bytes=0-9"})
        self.assertEqual((status, headers["Content-Type"]), (206, "video/mp4"))

    def test_config_validation_and_upload(self):
        self.assertEqual(self.post("/api/jobs/demo-job/config", {"voice": "nobody"})[0], 400)
        self.assertEqual(self.post("/api/jobs/demo-job/config", {"read": {"model": "x; rm -rf"}})[0], 400)
        status, _, _ = self.post("/api/jobs/demo-job/config", {"voice": "maichi", "read": {"engine": "manual"}, "gates": ["write"]})
        self.assertEqual(status, 200)
        self.assertEqual(self.job.config()["tts"]["voice"], "maichi")
        self.assertEqual(self.job.config()["gates"], ["write"])
        self.assertEqual(self.post("/api/jobs/demo-job/upload", {"kind": "review", "content": "{bad"})[0], 400)
        self.assertEqual(self.post("/api/jobs/demo-job/upload", {"kind": "timeline", "content": "---\n"})[0], 200)
        self.assertTrue(self.job.timeline.is_file())
        self.assertEqual(self.post("/api/jobs/demo-job/archive", {"confirm": "wrong"})[0], 400)


if __name__ == "__main__":
    unittest.main()
