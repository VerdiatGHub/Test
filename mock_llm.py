import json, time, http.server, socketserver
PORT=8787
VERDICT={"Title":"inventory-api Kafka consumer stuck in rebalance loop","Summary":"A previously-quiet service is emitting a burst of fatal errors indicating its Kafka consumer group is stuck rebalancing, causing message backlog across partitions and growing processing lag.","Severity":"high","Category":"messaging","Confidence":0.9,"Suggestions":["Restart the stuck consumer group","Check broker partition assignments","Inspect consumer lag metrics"],"reasoning":"Sudden burst of 20+ fatal errors from a service with no prior baseline."}
class H(http.server.BaseHTTPRequestHandler):
    def _send(self,obj,code=200):
        b=json.dumps(obj).encode(); self.send_response(code)
        self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path.startswith("/v1/models"): self._send({"object":"list","data":[{"id":"gemini-2.0-flash","object":"model"}]})
        else: self._send({"ok":True})
    def do_POST(self):
        ln=int(self.headers.get("Content-Length",0)); _=self.rfile.read(ln)
        resp={"id":"chatcmpl-mock","object":"chat.completion","created":int(time.time()),"model":"gemini-2.0-flash","choices":[{"index":0,"message":{"role":"assistant","content":json.dumps(VERDICT)},"finish_reason":"stop"}],"usage":{"prompt_tokens":100,"completion_tokens":50,"total_tokens":150}}
        self._send(resp)
    def log_message(self,*a): pass
with socketserver.TCPServer(("127.0.0.1",PORT),H) as s:
    s.serve_forever()
