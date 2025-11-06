from http.server import BaseHTTPRequestHandler, HTTPServer
from pymongo import MongoClient
import os, time

MONGO_HOST = os.getenv("MONGO_HOST", "cmtx-mongo")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_USER = os.getenv("MONGO_INITDB_ROOT_USERNAME")
MONGO_PASS = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
MONGO_DB   = os.getenv("MONGO_INITDB_DATABASE", "cmtxdb")

def client():
    uri = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"
    return MongoClient(uri, serverSelectionTimeoutMS=2000)

def get_message():
    c = client()
    col = c[MONGO_DB]["messages"]
    if col.count_documents({}) == 0:
        col.insert_one({"message": "Hola desde Mongo (PV) 👋", "ts": time.time()})
    doc = col.find_one({}, sort=[("_id", 1)])
    return doc.get("message", "Sin mensaje")

class H(BaseHTTPRequestHandler):
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
        self.send_response(404); self.end_headers()

if __name__ == "__main__":
    HTTPServer(("", 8080), H).serve_forever()