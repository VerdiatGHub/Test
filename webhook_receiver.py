import http.server, json, datetime, sys

LOG = r"C:\Users\Administrator\Desktop\Project\webhook_received.log"

class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8", "replace")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"\n===== {ts}  POST {self.path} =====\n{body}\n"
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(entry)
        print(entry, flush=True)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"code":0,"msg":"success"}')
    def log_message(self, *a): pass

http.server.HTTPServer(("127.0.0.1", 9000), H).serve_forever()
