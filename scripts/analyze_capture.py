"""Read what the interceptor SAW, decode the circuits actually sent, attack them, and emit a receipt. Reads captures/*.json."""
import argparse, glob, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from qpf import wire
from qpf.use_cases import oracle_attack

ap = argparse.ArgumentParser(); ap.add_argument("--dir", default="captures"); ap.add_argument("--out", default="artifacts/wire/receipt.json")
a = ap.parse_args(); secret = json.load(open(".local/secret.json"))["secret"]; rows = []
for f in sorted(glob.glob(f"{a.dir}/*.json")):
    rec = json.load(open(f)); body = rec.get("body_json")
    if body is None: continue
    for path, qc in wire.find_circuits(body):
        r = oracle_attack.recover(qc); hit = r.get("best") == secret and r.get("p_best", 0) > 0.5
        rows.append({"capture": pathlib.Path(f).name, "host": rec["host"], "json_path": path, "body_bytes": rec["body_bytes"],
                     "body_sha256": rec["body_sha256"][:16], "wire_qubits": qc.num_qubits, "wire_depth": qc.depth(),
                     "circuit_sha256": wire.circuit_hash(qc)[:16], "attack": r["status"], "recovered_matches_secret": r.get("best") == secret,
                     "p": round(r.get("p_best", 0), 3), "secret_exposed": hit, "decision": "BLOCK" if hit else "NO_EXPOSURE_FOUND_BY_THIS_ATTACK"})
pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True); json.dump(rows, open(a.out, "w"), indent=1)
print(f"{'capture':34s} {'qubits':>6s} {'depth':>5s} {'matches':>8s} {'p':>6s}  decision")
for r in rows: print(f"{r['capture'][:34]:34s} {r['wire_qubits']:6d} {r['wire_depth']:5d} {str(r['recovered_matches_secret']):>8s} {r['p']:6.3f}  {r['decision']}")
sys.exit(2 if any(r["secret_exposed"] for r in rows) else 0)
