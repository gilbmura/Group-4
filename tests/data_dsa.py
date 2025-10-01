import json
import threading
import time
import xml.etree.ElementTree as ET

# --------------------
# In-memory store and config for parsing
# --------------------
store_lock = threading.Lock()
transactions_list = []  # list[dict]
transactions_by_id = {}  # id -> dict
next_id = 1

# Heuristic hints for XML → records parsing.
RECORD_TAG_CANDIDATES = ["transaction", "sms", "record", "message", "entry", "item", "sms"]
FIELD_KEYS = {
    "id": ["id", "transaction_id", "msg_id", "uid"],
    "type": ["type", "txn_type", "transaction_type"],
    "amount": ["amount", "amt", "value"],
    "sender": ["sender", "from", "src", "payer", "msisdn_from", "address"],
    "receiver": ["receiver", "to", "dst", "payee", "msisdn_to"],
    "timestamp": ["timestamp", "time", "date", "datetime", "created_at", "readable_date"],
    "owner": ["owner", "user", "account", "username"],
}

def to_str(x):
    return "" if x is None else str(x).strip()

def pick_first_key(d, candidates):
    for c in candidates:
        if c in d and to_str(d[c]) != "":
            return d[c]
    return None

def infer_record_tag(root):
    counts = {}
    for elem in root.iter():
        tag = elem.tag.lower().split("}")[-1]
        if tag in RECORD_TAG_CANDIDATES:
            counts[tag] = counts.get(tag, 0) + 1
    if counts:
        return max(counts.items(), key=lambda kv: kv[1])[0]
    counts = {}
    for child in list(root):
        tag = child.tag.lower().split("}")[-1]
        counts[tag] = counts.get(tag, 0) + 1
    if counts:
        return max(counts.items(), key=lambda kv: kv[1])[0]
    return None

def xml_element_to_dict(elem):
    data = {}
    for k, v in elem.attrib.items():
        data[k.lower()] = to_str(v)
    for child in list(elem):
        k = child.tag.lower().split("}")[-1]
        if list(child):
            if child.text and to_str(child.text):
                data[k] = to_str(child.text)
        else:
            data[k] = to_str(child.text)
    if not data and elem.text and to_str(elem.text):
        data["text"] = to_str(elem.text)
    return data

def normalize_transaction(raw):
    global next_id
    d = dict(raw)
    rid = pick_first_key(d, FIELD_KEYS["id"])
    if not rid:
        rid = str(next_id)
        next_id += 1
    else:
        rid = str(rid)
    norm = {
        "id": rid,
        "type": to_str(pick_first_key(d, FIELD_KEYS["type"]) or d.get("type")),
        "amount": to_str(pick_first_key(d, FIELD_KEYS["amount"]) or d.get("amount")),
        "sender": to_str(pick_first_key(d, FIELD_KEYS["sender"]) or d.get("sender")),
        "receiver": to_str(pick_first_key(d, FIELD_KEYS["receiver"]) or d.get("receiver")),
        "timestamp": to_str(pick_first_key(d, FIELD_KEYS["timestamp"]) or d.get("timestamp")),
        "owner": to_str(pick_first_key(d, FIELD_KEYS["owner"]) or d.get("owner")),
        "_raw": d,
    }
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
        for elem in list(root):
            records.append(xml_element_to_dict(elem))
    with store_lock:
        transactions_list.clear()
        transactions_by_id.clear()
        next_id = 1
        for raw in records:
            tx = normalize_transaction(raw)
            transactions_list.append(tx)
            transactions_by_id[tx["id"]] = tx
            try:
                nid = int(tx["id"])
                if nid >= next_id:
                    next_id = nid + 1
            except ValueError:
                pass

def load_from_json(path):
    global next_id
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    with store_lock:
        transactions_list.clear()
        transactions_by_id.clear()
        next_id = 1
        for raw in data:
            tx = normalize_transaction(raw)
            transactions_list.append(tx)
            transactions_by_id[tx["id"]] = tx
            try:
                nid = int(tx["id"])
                next_id = max(next_id, nid + 1)
            except ValueError:
                pass

def snapshot_to_json(path):
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