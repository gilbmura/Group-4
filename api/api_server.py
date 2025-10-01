import base64
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from data_dsa import (
    store_lock,
    transactions_list,
    transactions_by_id,
    load_from_xml,
    load_from_json,
    snapshot_to_json,
    normalize_transaction,
    dict_lookup_by_id,
    benchmark_search,
)

# --------------------
# Config
# --------------------
XML_FILE = "modified_sms_v2 (1).xml"
JSON_SNAPSHOT = "transactions_snapshot.json"
HOST, PORT = "127.0.0.1", 8000

# Users and roles
USERS = {
    "group4": {"password": "member", "role": "admin"},
    "alice": {"password": "user123", "role": "user"},
    "bob": {"password": "user123", "role": "user"},
}

# --------------------
# Auth helpers and RBAC
# --------------------
def parse_basic_auth(header_val):
    if not header_val or not header_val.startswith("Basic "):
        return None, None
    try:
        decoded = base64.b64decode(header_val.split(" ", 1)[1]).decode("utf-8")
        username, password = decoded.split(":", 1)
        return username, password
    except Exception:
        return None, None

def authenticate(handler):
    auth = handler.headers.get("Authorization")
    username, password = parse_basic_auth(auth)
    if username in USERS and USERS[username]["password"] == password:
        return username, USERS[username]["role"]
    return None, None

def require_auth(handler):
    username, role = authenticate(handler)
    if not username:
        handler.send_response(401)
        handler.send_header("WWW-Authenticate", 'Basic realm="transactions"')
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
        return None, None
    return username, role

def can_read(username, role, tx):
    if role == "admin":
        return True
    return tx and tx.get("owner") == username

def can_write(username, role, tx):
    if role == "admin":
        return True
    return tx and tx.get("owner") == username

# --------------------
# HTTP handler
# --------------------
class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parse_id(self, path):
        parts = [p for p in path.split("/") if p]
        if len(parts) == 2 and parts[0] == "transactions":
            return parts[1]
        return None

    def do_GET(self):
        username, role = require_auth(self)
        if not username:
            return
        parsed = urlparse(self.path)
        if parsed.path == "/transactions":
            with store_lock:
                if role == "admin":
                    data = transactions_list[:]
                else:
                    data = [tx for tx in transactions_list if can_read(username, role, tx)]
            self._send_json(200, data)
            return
        tx_id = self._parse_id(parsed.path)
        if tx_id:
            tx = dict_lookup_by_id(tx_id)
            if not tx:
                self._send_json(404, {"error": "Not found"})
                return
            if not can_read(username, role, tx):
                self._send_json(403, {"error": "Forbidden"})
                return
            self._send_json(200, tx)
            return
        if parsed.path == "/dsa/benchmark":
            with store_lock:
                sample_ids = [tx["id"] for tx in transactions_list[:20]] or [tx["id"] for tx in transactions_list]
            result = benchmark_search(sample_ids, repeats=500)
            self._send_json(200, {"sample_count": len(sample_ids), **result})
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        username, role = require_auth(self)
        if not username:
            return
        parsed = urlparse(self.path)
        if parsed.path == "/transactions":
            length = int(self.headers.get("Content-Length", "0"))
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON"})
                return
            tx = normalize_transaction(payload)
            if role != "admin":
                tx["owner"] = username
            with store_lock:
                if tx["id"] in transactions_by_id:
                    self._send_json(409, {"error": "ID already exists"})
                    return
                transactions_by_id[tx["id"]] = tx
                transactions_list.append(tx)
            snapshot_to_json(JSON_SNAPSHOT)
            self._send_json(201, tx)
            return
        self._send_json(404, {"error": "Not found"})

    def do_PUT(self):
        username, role = require_auth(self)
        if not username:
            return
        tx_id = self._parse_id(urlparse(self.path).path)
        if not tx_id:
            self._send_json(404, {"error": "Not found"})
            return
        with store_lock:
            existing = transactions_by_id.get(tx_id)
        if not existing:
            self._send_json(404, {"error": "Not found"})
            return
        if not can_write(username, role, existing):
            self._send_json(403, {"error": "Forbidden"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return
        payload["id"] = tx_id
        if role != "admin":
            payload["owner"] = existing["owner"]
        updated = normalize_transaction({**existing, **payload})
        with store_lock:
            transactions_by_id[tx_id] = updated
            for i, tx in enumerate(transactions_list):
                if tx["id"] == tx_id:
                    transactions_list[i] = updated
                    break
        snapshot_to_json(JSON_SNAPSHOT)
        self._send_json(200, updated)

    def do_DELETE(self):
        username, role = require_auth(self)
        if not username:
            return
        tx_id = self._parse_id(urlparse(self.path).path)
        if not tx_id:
            self._send_json(404, {"error": "Not found"})
            return
        with store_lock:
            existing = transactions_by_id.get(tx_id)
            if not existing:
                self._send_json(404, {"error": "Not found"})
                return
            if not can_write(username, role, existing):
                self._send_json(403, {"error": "Forbidden"})
                return
            del transactions_by_id[tx_id]
            for i, tx in enumerate(transactions_list):
                if tx["id"] == tx_id:
                    transactions_list.pop(i)
                    break
        snapshot_to_json(JSON_SNAPSHOT)
        self._send_json(204, {"status": "deleted"})

    def log_message(self, format, *args):
        return

def main():
    # Choose one source of truth to load from on startup:
    # Option A: XML (your current file)
    load_from_xml(XML_FILE)
    # Option B: JSON snapshot
    # load_from_json(JSON_SNAPSHOT)

    print(f"Loaded {len(transactions_list)} transactions")
    print(f"Starting server at http://{HOST}:{PORT}")
    with HTTPServer((HOST, PORT), Handler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    main()