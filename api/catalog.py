"""Vercel serverless function: GET /api/catalog -> product catalog JSON."""
from http.server import BaseHTTPRequestHandler
import json

from _core import CATALOG


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = json.dumps(CATALOG).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
