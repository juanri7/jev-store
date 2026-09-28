"""Vercel serverless function: POST /api/profile -> Noul interest probabilities."""
from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _core import MAX_BODY_BYTES, profile_endpoint


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = min(int(self.headers.get("Content-Length", 0) or 0), MAX_BODY_BYTES)
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw or b"{}")
        except Exception:  # noqa: BLE001
            body = {}
        out = profile_endpoint(body) if isinstance(body, dict) else {"probs": {}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.send_response(405)
        self.end_headers()
