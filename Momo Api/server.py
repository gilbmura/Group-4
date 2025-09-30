import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

# --------------------
# Config
# --------------------
XML_FILE = "modified_sms_v2 (1).xml"
JSON_SNAPSHOT = "transactions_snapshot.json"  # optional persistence
HOST, PORT = "127.0.0.1", 8000

# For role-based auth: admin has full access; user can only access own transactions.
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    # Add user accounts here. The username is used as owner key.
    "alice": {"password": "user123", "role": "user"},
    "bob": {"password": "user123", "role": "user"},
}

# Heuristic hints for XML → records parsing.
# 1) Candidate element names that may contain transactions
RECORD_TAG_CANDIDATES = ["transaction", "sms", "record", "message", "entry", "item"]

# 2) Field name mapping preferences; we will pick from attributes/text when present.
FIELD_KEYS = {
    "id": ["id", "transaction_id", "msg_id", "uid"],
    "type": ["type", "txn_type", "transaction_type"],
    "amount": ["amount", "amt", "value"],
    "sender": ["sender", "from", "src", "payer", "msisdn_from"],
    "receiver": ["receiver", "to", "dst", "payee", "msisdn_to"],
    "timestamp": ["timestamp", "time", "date", "datetime", "created_at"],
    "owner": ["owner", "user", "account", "username"],
}

# If the XML has nested elements with those names rather than attributes, we will read .text
# If none match, we will still produce a dict of all attributes as a fallback.


# --------------------
# In-memory store with both list and dict for DSA demo
# --------------------
store_lock = threading.Lock()
transactions_list = []  # list of dicts
transactions_by_id = {}  # id -> dict
next_id = 1  # assigned when missing

def to_str(x):
    return "" if x is None else str(x).strip()

def pick_first_key(d, candidates):
    for c in candidates:
        if c in d and to_str(d[c]) != "":
            return d[c]
    return None

def infer_record_tag(root):
    # Find the most frequent child tag under root among candidates
    counts = {}
    for elem in root.iter():
        tag = elem.tag.lower().split("}")[-1]  # strip namespace if any
        if tag in RECORD_TAG_CANDIDATES:
            counts[tag] = counts.get(tag, 0) + 1
    if counts:
        return max(counts.items(), key=lambda kv: kv[1])[0]
    # fallback: pick the most frequent non-root tag
    counts = {}
    for child in list(root):
        tag = child.tag.lower().split("}")[-1]
        counts[tag] = counts.get(tag, 0) + 1
    if counts:
        return max(counts.items(), key=lambda kv: kv[1])[0]
    return None

def xml_element_to_dict(elem):
    # flatten attributes + child elements into a single dict of strings
    data = {}
    for k, v in elem.attrib.items():
        data[k.lower()] = to_str(v)
    for child in list(elem):
        k = child.tag.lower().split("}")[-1]
        if list(child):
            # nested structure → naive flatten: child.text only if leaf-ish
            if child.text and to_str(child.text):
                data[k] = to_str(child.text)
        else:
            data[k] = to_str(child.text)
    # as last resort, if element has text and no attributes
    if not data and elem.text and to_str(elem.text):
        data["text"] = to_str(elem.text)
    return data

def normalize_transaction(raw):
    global next_id
    # Try to map common fields
    # Clone to avoid mutating original
    d = dict(raw)

    # ID
    rid = pick_first_key(d, FIELD_KEYS["id"])
    if not rid:
        rid = str(next_id)
        next_id += 1
    else:
        rid = str(rid)

    # Preferred normalized keys
    norm = {
        "id": rid,
        "type": to_str(pick_first_key(d, FIELD_KEYS["type"]) or d.get("type")),
        "amount": to_str(pick_first_key(d, FIELD_KEYS["amount"]) or d.get("amount")),
        "sender": to_str(pick_first_key(d, FIELD_KEYS["sender"]) or d.get("sender")),
        "receiver": to_str(pick_first_key(d, FIELD_KEYS["receiver"]) or d.get("receiver")),
        "timestamp": to_str(pick_first_key(d, FIELD_KEYS["timestamp"]) or d.get("timestamp")),
        "owner": to_str(pick_first_key(d, FIELD_KEYS["owner"]) or d.get("owner")),
        "_raw": d,  # keep full original mapping for transparency
    }

    # If no owner provided, we can default to sender for demo RBAC
    if not norm["owner"]:
        norm["owner"] = norm["sender"] or "unknown"

    return norm

def load_from_xml(xml_path):
    global next_id
    tree = ET.parse(xml_path)
    root = tree.getroot()
    record_tag = infer_record_tag(root)

    records = []
    if record_tag:
        for elem in root.iter():
            tag = elem.tag.lower().split("}")[-1]
            if tag == record_tag:
                records.append(xml_element_to_dict(elem))
    else:
        # fallback: each direct child is a record
        for elem in list(root):
            records.append(xml_element_to_dict(elem))

    # normalize and build indexes
    with store_lock:
        transactions_list.clear()
        transactions_by_id.clear()
        next_id = 1
        for raw in records:
            tx = normalize_transaction(raw)
            transactions_list.append(tx)
            transactions_by_id[tx["id"]] = tx
            try:
                # keep next_id > max existing id if numeric
                nid = int(tx["id"])
                if nid >= next_id:
                    next_id = nid + 1
            except ValueError:
                pass

def snapshot_to_json(path=JSON_SNAPSHOT):
    with store_lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(transactions_list, f, ensure_ascii=False, indent=2)

# --------------------
# DSA: linear search vs dict lookup
# --------------------
def linear_search_by_id(target_id):
    with store_lock:
        for tx in transactions_list:
            if tx["id"] == target_id:
                return tx
    return None

def dict_lookup_by_id(target_id):
    with store_lock:
        return transactions_by_id.get(target_id)

def benchmark_search(sample_ids, repeats=1000):
    t0 = time.time()
    for _ in range(repeats):
        for i in sample_ids:
            _ = linear_search_by_id(i)
    t1 = time.time()
    for _ in range(repeats):
        for i in sample_ids:
            _ = dict_lookup_by_id(i)
    t2 = time.time()
    return {"linear_sec": t1 - t0, "dict_sec": t2 - t1}

# --------------------
# Auth helpers
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
    # users can only modify/delete their own transactions
    return tx and tx.get("owner") == username

# --------------------
# HTTP Handler
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
            # list all, filtered by RBAC
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

            # Normalize and enforce ownership for non-admins
            tx = normalize_transaction(payload)
            if role != "admin":
                tx["owner"] = username  # force ownership to caller

            with store_lock:
                if tx["id"] in transactions_by_id:
                    self._send_json(409, {"error": "ID already exists"})
                    return
                transactions_by_id[tx["id"]] = tx
                transactions_list.append(tx)
            snapshot_to_json()
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

        # Do not allow ID change
        payload["id"] = tx_id
        # Non-admins cannot change owner away from themselves
        if role != "admin":
            payload["owner"] = existing["owner"]

        updated = normalize_transaction({**existing, **payload})
        with store_lock:
            transactions_by_id[tx_id] = updated
            # update list in place
            for i, tx in enumerate(transactions_list):
                if tx["id"] == tx_id:
                    transactions_list[i] = updated
                    break
        snapshot_to_json()
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
        snapshot_to_json()
        self._send_json(204, {"status": "deleted"})

    # Quiet default logging
    def log_message(self, format, *args):
        return

def main():
    print(f"Loading XML from {XML_FILE} ...")
    load_from_xml(XML_FILE)
    print(f"Loaded {len(transactions_list)} transactions")
    print(f"Starting server at http://{HOST}:{PORT}")
    with HTTPServer((HOST, PORT), Handler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    main()