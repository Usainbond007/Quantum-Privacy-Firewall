"""LOCAL MOCK of a job endpoint (offline rehearsal ONLY; it is not a real quantum service and proves nothing about one).
  python scripts/mock_runtime_server.py 8765                       -> plain HTTP
  python scripts/mock_runtime_server.py 8443 certs/localhost.pem certs/localhost.key   -> HTTPS (needed to practise TLS decryption)"""
import json, sys, ssl
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); self.rfile.read(n)
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps({"id": "mock-job", "mock": True}).encode())
    def log_message(self, *a): pass
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765; srv = HTTPServer(("127.0.0.1", port), H)
    if len(sys.argv) > 3:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(sys.argv[2], sys.argv[3]); srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    srv.serve_forever()
