"""Loopback synthetic OpenAI-compatible responder for manual Docker UI acceptance only."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        assert self.path == "/v1/chat/completions" and payload["model"] == "synthetic-ui-model"
        result = json.dumps({"choices": [{"message": {"content": "Synthetic connection test OK"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(result)))
        self.end_headers()
        self.wfile.write(result)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    if os.environ.get("DATA_MODE") != "fixtures":
        raise SystemExit("Synthetic responder requires fixture mode")
    ThreadingHTTPServer(("127.0.0.1", 14000), Handler).serve_forever()
