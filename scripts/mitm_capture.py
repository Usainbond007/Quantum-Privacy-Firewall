"""mitmproxy addon: save the request BODIES a quantum client sends, with credentials stripped.
Run:  mitmdump -s scripts/mitm_capture.py --set qpf_dir=captures
Only hosts matching QPF_HOSTS (default: quantum / ibm) are saved. Auth endpoints (IAM) are NEVER saved: their bodies hold API keys."""
import json, os, pathlib, time, hashlib
from mitmproxy import ctx, http

SKIP_HOST_PARTS = ("iam.", "login.", "auth.")
KEEP_HOST_PARTS = tuple(os.environ.get("QPF_HOSTS", "quantum,ibm,localhost,127.0.0.1").split(","))
REDACT = {"authorization", "cookie", "service-crn", "x-api-key", "x-access-token"}

def load(loader): loader.add_option("qpf_dir", str, "captures", "where to write captured requests")

def request(flow: http.HTTPFlow):
    h = flow.request.pretty_host.lower()
    if any(s in h for s in SKIP_HOST_PARTS) or not any(k in h for k in KEEP_HOST_PARTS): return
    if flow.request.method not in ("POST", "PUT", "PATCH") or not flow.request.content: return
    d = pathlib.Path(ctx.options.qpf_dir); d.mkdir(parents=True, exist_ok=True)
    body = flow.request.content
    rec = {"t": time.time(), "method": flow.request.method, "host": h, "path": flow.request.path,
           "http_version": flow.request.http_version, "body_bytes": len(body), "body_sha256": hashlib.sha256(body).hexdigest(),
           "headers": {k: ("<redacted>" if k.lower() in REDACT else v) for k, v in flow.request.headers.items()}}
    try: rec["body_json"] = json.loads(body)
    except Exception: rec["body_raw_hex_head"] = body[:64].hex()
    name = f"{int(time.time()*1000)}_{flow.request.method}_{h.replace(':','_')}.json"
    (d / name).write_text(json.dumps(rec, indent=1)); ctx.log.info(f"[qpf] saved {name} ({len(body)} bytes)")
