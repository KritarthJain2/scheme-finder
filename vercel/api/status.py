"""Vercel serverless /api/status — reports only whether keys are configured, never the keys."""
import json
import os
from http.server import BaseHTTPRequestHandler

NEBIUS_MODEL = os.environ.get("NEBIUS_MODEL", "nvidia/nemotron-3-nano-omni")


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = json.dumps({
            "nebius_configured": bool(os.environ.get("NEBIUS_API_KEY", "")),
            "tavily_configured": bool(os.environ.get("TAVILY_API_KEY", "")),
            "model": NEBIUS_MODEL,
            "mode": "real" if os.environ.get("TAVILY_API_KEY", "") else "not-configured",
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
