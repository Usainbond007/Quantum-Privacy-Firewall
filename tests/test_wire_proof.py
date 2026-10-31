import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from qpf import wire, defenses, verification, compilation
from qpf.use_cases import grover, oracle_attack

SECRET = "1011"

def test_roundtrip_and_scan_finds_circuit_in_nested_json():
    qc = grover.with_measurements(grover.grover_kernel(SECRET))
    body = {"a": {"pubs": [[wire.encode_circuit(qc, compress=True), [0.1, 0.2]]]}, "shots": 10}
    found = list(wire.find_circuits(body)); assert len(found) == 1
    assert wire.circuit_hash(found[0][1]) == wire.circuit_hash(qc)

def test_exact_attack_recovers_secret_logically():
    r = oracle_attack.recover(grover.with_measurements(grover.grover_kernel(SECRET)))
    assert r["best"] == SECRET and r["p_best"] > 0.9

def test_verified_rewrites_change_bytes_but_not_the_secret():
    k = grover.grover_kernel(SECRET); base, _ = compilation.compile_circuit(grover.with_measurements(k), 1, 7, None)
    for strat in ("decomp", "reorder", "decomp+reorder+layout"):
        cand, layout = defenses.apply_strategy(k, strat, 3)
        assert verification.verify(k, cand).status == "PASS"                     # correct ...
        tc, _ = compilation.compile_circuit(grover.with_measurements(cand), 1, 3, layout)
        assert wire.circuit_hash(tc) != wire.circuit_hash(base)                  # ... different on the wire ...
        assert oracle_attack.recover(tc)["best"] == SECRET                       # ... still readable => policy must BLOCK

def test_inequivalent_candidate_is_caught():
    k = grover.grover_kernel(SECRET); bad = grover.grover_kernel("1010")
    assert verification.verify(k, bad).status == "FAIL"
