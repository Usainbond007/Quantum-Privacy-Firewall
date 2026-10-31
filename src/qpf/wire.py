"""What actually leaves the machine. Encode/decode circuits the way job payloads carry them (QPY -> base64 inside JSON),
and recover circuits from ANY captured request body by scanning every string for a decodable QPY blob.
Format-tolerant on purpose: we do not assume a vendor's exact schema, we look at what was really sent."""
import base64, binascii, hashlib, io, json, zlib
from qiskit import qpy

def encode_circuit(qc, compress=False):
    buf = io.BytesIO(); qpy.dump(qc, buf); raw = buf.getvalue()
    return base64.b64encode(zlib.compress(raw) if compress else raw).decode()

def decode_blob(s):
    """str -> list[QuantumCircuit] or [] (never raises)."""
    try: raw = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError): return []
    for cand in (raw, _z(raw)):
        if cand and cand[:4] == b"QISK":
            try: return list(qpy.load(io.BytesIO(cand)))
            except Exception: return []
    return []

def _z(raw):
    try: return zlib.decompress(raw)
    except Exception: return None

def find_circuits(obj, path="$"):
    """Walk parsed JSON; yield (json_path, circuit) for every embedded QPY circuit."""
    if isinstance(obj, str):
        if len(obj) > 64:
            for k, c in enumerate(decode_blob(obj)): yield f"{path}[{k}]", c
    elif isinstance(obj, dict):
        for k, v in obj.items(): yield from find_circuits(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj): yield from find_circuits(v, f"{path}[{i}]")

def find_numeric_payload(obj, path="$", out=None):
    """Collect numeric arrays (candidate parameter bindings) so a direct-exposure check can look at them."""
    out = {} if out is None else out
    if isinstance(obj, list) and obj and all(isinstance(x, (int, float)) for x in obj): out[path] = obj
    elif isinstance(obj, list):
        for i, v in enumerate(obj): find_numeric_payload(v, f"{path}[{i}]", out)
    elif isinstance(obj, dict):
        for k, v in obj.items(): find_numeric_payload(v, f"{path}.{k}", out)
    return out

def body_hash(body: bytes): return hashlib.sha256(body).hexdigest()
def circuit_hash(qc):
    buf = io.BytesIO(); qpy.dump(qc, buf); return hashlib.sha256(buf.getvalue()).hexdigest()

def parse_body(body: bytes):
    try: return json.loads(body)
    except Exception:
        try: return json.loads(zlib.decompress(body))
        except Exception: return None
