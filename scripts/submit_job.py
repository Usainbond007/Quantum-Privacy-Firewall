"""Submit the Grover case as ORIGINAL or QPF-PROTECTED. The secret never leaves .local/ (gitignored).
  --target mock : POST the job JSON to the local mock server (offline rehearsal)
  --target ibm  : submit through qiskit-ibm-runtime SamplerV2 to a real backend using YOUR saved account
Route through an interceptor with:  HTTPS_PROXY=http://127.0.0.1:8080  REQUESTS_CA_BUNDLE=~/.mitmproxy/mitmproxy-ca-cert.pem"""
import argparse, hashlib, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from qpf import compilation, defenses, verification, wire
from qpf.use_cases import grover

ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=["original", "protected"], required=True)
ap.add_argument("--target", choices=["mock", "ibm"], default="mock")
ap.add_argument("--secret", default="1011"); ap.add_argument("--strategy", default="decomp+reorder+layout")
ap.add_argument("--seed", type=int, default=2); ap.add_argument("--backend", default=None)
ap.add_argument("--shots", type=int, default=256); ap.add_argument("--url", default="http://127.0.0.1:8765/jobs")
a = ap.parse_args()

kernel = grover.grover_kernel(a.secret); local = pathlib.Path(".local"); local.mkdir(exist_ok=True)
(local / "secret.json").write_text(json.dumps({"secret": a.secret}))            # evaluation ground truth, local only
verdict = {"status": "PASS", "method": "identical_logical_circuit"}
cand, layout = kernel, None
if a.mode == "protected":
    cand, layout = defenses.apply_strategy(kernel, a.strategy, a.seed)
    v = verification.verify(kernel, cand); verdict = {"status": v.status, "method": v.method}
    if v.status != "PASS": sys.exit(f"refusing to submit: verification {v.status}")      # fail closed
payload_qc = grover.with_measurements(cand)

if a.target == "mock":
    import requests
    tc, _ = compilation.compile_circuit(payload_qc, 1, a.seed, layout)
    body = {"program_id": "sampler", "params": {"pubs": [[wire.encode_circuit(tc)]], "shots": a.shots}}
    data = json.dumps(body).encode()                                   # exact bytes we send, so they can be hashed
    r = requests.post(a.url, data=data, headers={"Content-Type": "application/json"}, timeout=30); print("mock response", r.status_code)
    sent_sha = hashlib.sha256(data).hexdigest(); print("BODY_SHA256_SENT", sent_sha, "bytes", len(data))
else:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    svc = QiskitRuntimeService(); be = svc.backend(a.backend) if a.backend else svc.least_busy(operational=True, simulator=False)
    pm = generate_preset_pass_manager(backend=be, optimization_level=1, seed_transpiler=a.seed, initial_layout=layout)
    isa = pm.run(payload_qc); job = SamplerV2(mode=be).run([isa], shots=a.shots); print("submitted", job.job_id(), "on", be.name)
print(json.dumps({"mode": a.mode, "verification": verdict, "circuit_sha256_local": wire.circuit_hash(payload_qc)}))
