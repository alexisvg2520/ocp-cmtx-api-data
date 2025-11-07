from http.server import BaseHTTPRequestHandler, HTTPServer
from pymongo import MongoClient
import os, time, socket, contextlib

MONGO_HOST = os.getenv("MONGO_HOST", "cmtx-mongo")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_USER = os.getenv("MONGO_INITDB_ROOT_USERNAME")
MONGO_PASS = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
MONGO_DB   = os.getenv("MONGO_INITDB_DATABASE", "cmtxdb")

def get_client():
    uri = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
    return MongoClient(uri, serverSelectionTimeoutMS=3000)

def get_message():
    c = get_client()
    col = c[MONGO_DB]["messages"]
    if col.count_documents({}) == 0:
        col.insert_one({"message": "Hola desde Mongo (PV) 👋"})
    doc = col.find_one({}, sort=[("_id", 1)])
    return doc.get("message", "Sin mensaje")

class H(BaseHTTPRequestHandler):
    def _diagnose_mongo(self) -> str:
        lines = [f"MONGO={MONGO_HOST}:{MONGO_PORT} db={MONGO_DB}"]
        try:
            with open("/etc/resolv.conf", "r", encoding="utf-8") as fh:
                nameservers = [ln.strip() for ln in fh if ln.startswith("nameserver")]
            if nameservers:
                lines.append("resolv.conf " + ", ".join(nameservers))
        except OSError as e:
            lines.append(f"resolv.conf ✖ {e}")
        try:
            infos = socket.getaddrinfo(MONGO_HOST, MONGO_PORT, proto=socket.IPPROTO_TCP)
            uniq = sorted({f"{info[4][0]}:{info[4][1]}" for info in infos})
            lines.append("DNS ✔ " + ", ".join(uniq))
        except socket.gaierror as e:
            lines.append(f"DNS ✖ {e}")
        try:
            with contextlib.closing(socket.create_connection((MONGO_HOST, MONGO_PORT), timeout=2)):
                lines.append("TCP CONNECT ✔")
        except OSError as e:
            lines.append(f"TCP CONNECT ✖ {e}")
        try:
            client = get_client()
            client.admin.command("ping")
            lines.append("Mongo ping ✔")
        except Exception as e:
            lines.append(f"Mongo ping ✖ {e}")
        return "\n".join(lines)

    def do_GET(self):
        if self.path == "/data":
            try:
                msg = get_message()
                self.send_response(200); self.end_headers()
                self.wfile.write(f"{msg}".encode())
            except Exception as e:
                self.send_response(500); self.end_headers()
                self.wfile.write(f"mongo error: {e}".encode())
            return
        if self.path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok"); return
        if self.path == "/diag":
            self.send_response(200); self.end_headers(); self.wfile.write(self._diagnose_mongo().encode())
            return
        self.send_response(404); self.end_headers()

if __name__ == "__main__":
    HTTPServer(("", 8080), H).serve_forever()
