"""Pre-submission checks for two job types: a small Grover search and a QAOA portfolio job.

Each check names the fact to protect, the observer, and the attacks that were actually run,
then returns a release decision. Nothing here claims secrecy: an equivalence-checked rewrite
keeps the same function, so a decision of BLOCK is a normal outcome.
"""

import csv, hashlib, json, re, time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter, ParameterVector
from qiskit.circuit.library import XXPlusYYGate
from qiskit.quantum_info import Statevector
from . import compilation, defenses
from .verification import verify

GROVER_STRATEGIES = ["decomp", "reorder", "decomp+reorder"]
MARKED_RE = re.compile(r"^[01]{4}$")
DATA = Path(__file__).resolve().parents[2] / "data" / "qiskit_qmoo_market_data.csv"
DATA_URL = "https://raw.githubusercontent.com/Qiskit/documentation/main/datasets/tutorials/qmoo/market_data.csv"
ASSETS = ["AAPL", "MSFT", "XOM", "JPM", "JNJ", "PG", "NEE", "AMT"]
K = 4
PREFERENCES = {
    "risk_first": (1.0, 0.2),
    "balanced": (0.6, 0.6),
    "return_first": (0.2, 1.0),
}
GAMMA, BETA = 6.0, 0.5


def _circuit_hash(qc):
    """Canonical full SHA-256 for this bounded unitary workload, including parameters."""
    ops = [
        (
            i.operation.name,
            [qc.find_bit(q).index for q in i.qubits],
            [str(p) for p in i.operation.params],
        )
        for i in qc.data
    ]
    return hashlib.sha256(
        json.dumps(
            [qc.num_qubits, str(qc.global_phase), ops], separators=(",", ":")
        ).encode()
    ).hexdigest()


def _evidence(logical, compiled):
    from dataclasses import asdict
    from backend.app.services.verification import verify_compiled

    return asdict(verify_compiled(logical, compiled))


def _view(qc):
    from backend.app.services.serialization import serialize_circuit

    return serialize_circuit(qc)


def _metrics(tc):
    ops = tc.count_ops()
    return dict(
        depth=tc.depth(),
        n2q=int(sum(v for k, v in ops.items() if k in ("cz", "cx", "ecr"))),
        size=tc.size(),
    )


# ----------------------------------------------------------------------------- Grover


def grover_circuit(marked, iterations=3):
    bits = [int(b) for b in marked[::-1]]  # qubit i holds bit i of the string
    n = len(bits)

    def mcz(qc):
        qc.h(n - 1)
        qc.mcx(list(range(n - 1)), n - 1)
        qc.h(n - 1)

    qc = QuantumCircuit(n)
    qc.h(range(n))
    for _ in range(iterations):
        for i, b in enumerate(bits):
            if b == 0:
                qc.x(i)
        mcz(qc)
        for i, b in enumerate(bits):
            if b == 0:
                qc.x(i)
        qc.h(range(n))
        qc.x(range(n))
        mcz(qc)
        qc.x(range(n))
        qc.h(range(n))
    return qc


def pattern_reader(qc):
    """Naive structural attacker: reads X gates in front of the first multi-controlled gate."""
    n = qc.num_qubits
    has_x = set()
    for inst in qc.data:
        if inst.operation.name == "mcx":
            break
        if inst.operation.name == "x":
            has_x.add(qc.find_bit(inst.qubits[0]).index)
    return "".join("0" if i in has_x else "1" for i in reversed(range(n)))


def exact_reader(qc):
    """Exact attacker for small width: simulate the circuit and take the most likely outcome."""
    probs = Statevector(qc).probabilities_dict()
    guess = max(probs, key=probs.get)
    return guess, float(probs[guess])


def grover_check(
    marked, budget=0.2, opt_level=2, transpile_seed=11, seeds=(1, 2, 3, 4)
):
    started = time.perf_counter()
    if not np.isfinite(budget) or not 0 <= budget <= 0.5:
        raise ValueError("budget must be between 0 and 0.5")
    if not MARKED_RE.fullmatch(marked):
        raise ValueError("marked state must be four bits, e.g. 1011")
    base = grover_circuit(marked)
    tb, _ = compilation.compile_circuit(base, opt_level, transpile_seed)
    base_m = _metrics(tb)
    baseline_compiled = _evidence(base, tb)
    g0, p0 = exact_reader(base)
    out = dict(
        marked=marked,
        budget=budget,
        observer="holder of the submitted circuit file",
        baseline=dict(
            metrics=base_m,
            pattern_guess=pattern_reader(base),
            exact_guess=g0,
            exact_probability=p0,
            circuit_hash=_circuit_hash(base),
            circuit=_view(base),
            compiled_verification=baseline_compiled,
            probabilities=Statevector(base).probabilities().tolist(),
        ),
        candidates=[],
    )
    k = 0
    for strat in GROVER_STRATEGIES:
        for seed in seeds:
            k += 1
            cand, layout = defenses.apply_strategy(base, strat, seed)
            v = verify(base, cand)
            tc, _ = compilation.compile_circuit(cand, opt_level, transpile_seed, layout)
            m = _metrics(tc)
            cv = _evidence(base, tc)
            pg = pattern_reader(cand)
            eg, ep = exact_reader(cand)
            oh = dict(
                depth=m["depth"] / base_m["depth"] - 1,
                n2q=m["n2q"] / max(base_m["n2q"], 1) - 1,
            )
            out["candidates"].append(
                dict(
                    id=f"c{k:02d}",
                    strategy=strat,
                    seed=seed,
                    verification=v.status,
                    method=v.method,
                    metrics=m,
                    overhead=oh,
                    within_budget=max(oh.values()) <= budget,
                    compiled_verification=cv,
                    circuit=_view(cand),
                    total_variation=float(
                        np.abs(
                            Statevector(base).probabilities()
                            - Statevector(cand).probabilities()
                        ).sum()
                        / 2
                    ),
                    pattern_guess=pg,
                    pattern_recovers=pg == marked,
                    exact_guess=eg,
                    exact_probability=ep,
                    exact_recovers=eg == marked,
                    circuit_hash=_circuit_hash(cand),
                )
            )
    ok = [
        c
        for c in out["candidates"]
        if c["verification"] == "PASS"
        and c["compiled_verification"]["status"] == "PASS"
        and c["within_budget"]
    ]
    ok.sort(key=lambda c: (c["pattern_recovers"], max(c["overhead"].values())))
    sel = ok[0] if ok else None
    out["selected"] = sel["id"] if sel else None
    exact_rate = float(
        np.mean(
            [
                c["exact_recovers"]
                for c in out["candidates"]
                if c["verification"] == "PASS"
            ]
            or [0]
        )
    )
    pattern_rate = float(
        np.mean(
            [
                c["pattern_recovers"]
                for c in out["candidates"]
                if c["verification"] == "PASS"
            ]
            or [0]
        )
    )
    out["summary"] = dict(
        verified=sum(c["verification"] == "PASS" for c in out["candidates"]),
        total=len(out["candidates"]),
        pattern_recovery_rate=pattern_rate,
        exact_recovery_rate=exact_rate,
    )
    reasons = []
    if sel is None:
        status = "BLOCK"
        reasons.append(
            "No candidate passed logical and compiled verification within the overhead budget."
        )
    elif sel["exact_recovers"]:
        status = "BLOCK"
        reasons.append(
            f"The exact simulator identifies the marked state as the most likely output ({sel['exact_probability']:.2%} output probability)."
        )
        reasons.append(
            "The rewrite is verified equivalent, so it keeps the same oracle by construction."
        )
    else:
        status = "WARN"
        reasons.append(
            "Exact recovery failed on this circuit; other observers were not tested."
        )
    if sel and not sel["pattern_recovers"] and base is not None:
        reasons.append(
            "The pattern reader no longer finds the marked state, but that only defeats one attacker."
        )
    out["decision"] = dict(status=status, reasons=reasons)
    out["receipt"] = dict(
        circuit_hash=sel["circuit_hash"] if sel else None,
        target=f"FakeNighthawk, optimization level {opt_level}",
        verification=sel["method"] if sel else None,
        attacker="exact simulation, 4 qubits",
        decision=status,
        contains_predicate=False,
    )
    out["scope"] = [
        "Four-bit marked state: 16 possibilities, a pipeline demonstration and not a secret.",
        "Attacks inspect logical artifacts; compiled layout equivalence is checked separately. No compiled-artifact recovery attack is measured.",
        "Noiseless simulation only; no hardware or noise-model utility results.",
        "Family-level leakage numbers are the saved benchmark results, not computed here.",
    ]
    out["elapsed_seconds"] = time.perf_counter() - started
    out["receipt"].update(
        schema_version="2",
        compiled_verification=(
            sel["compiled_verification"]["status"] if sel else "UNKNOWN"
        ),
        budget=budget,
        enforcement="local assessment only; no cloud submission",
    )
    return out


# ----------------------------------------------------------------------------- portfolio


def load_market():
    with open(DATA, newline="") as f:
        rows = list(csv.DictReader(f))
    by = {r["ticker"]: r for r in rows}
    mu = np.array([float(by[a]["mu"]) for a in ASSETS])
    sigma = np.array([[float(by[a][b]) for b in ASSETS] for a in ASSETS])
    sha = hashlib.sha256(DATA.read_bytes()).hexdigest()
    return mu, sigma, sha


def _coefficients(mu, sigma):
    """Ising terms of x^T S x (risk) and mu^T x (return), x = (1 - z) / 2.
    Returns per-pair J, per-asset h for each term so the weights enter linearly."""
    n = len(mu)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    J_r = np.array([sigma[i, j] / 2 for i, j in pairs])
    h_r = np.array([-sigma[i].sum() / 2 for i in range(n)])
    h_m = np.array([mu[i] / 2 for i in range(n)])  # -mu^T x contributes +mu_i z_i / 2
    return pairs, J_r, h_r, h_m


def bindings_for(weights, mu, sigma):
    c_r, c_m = weights
    pairs, J_r, h_r, h_m = _coefficients(mu, sigma)
    h = c_r * h_r + c_m * h_m
    return np.concatenate([2 * GAMMA * h, 2 * GAMMA * c_r * J_r, [2 * BETA]])


def portfolio_template(n=8):
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    theta = ParameterVector("t", n + len(pairs))
    beta = Parameter("b")
    qc = QuantumCircuit(n)
    for i in range(K):
        qc.x(i)
    # A cost phase on a basis state is only a global phase. Mix BEFORE the cost
    # as well as after it, so interference carries objective information.
    for i in range(n):
        qc.append(XXPlusYYGate(1.1), [i, (i + 1) % n])
    for i in range(n):
        qc.rz(theta[i], i)
    for k, (i, j) in enumerate(pairs):
        qc.rzz(theta[n + k], i, j)
    for i in range(n):
        qc.append(XXPlusYYGate(beta), [i, (i + 1) % n])
    return qc, list(theta) + [beta]


def _bind(template, params, vec):
    return template.assign_parameters(dict(zip(params, [float(v) for v in vec])))


def _top_feasible(qc, m=6):
    probs = Statevector(qc).probabilities_dict()
    feas = {s: p for s, p in probs.items() if s.count("1") == K}
    return sorted(feas, key=feas.get, reverse=True)[:m]


def _portfolio_stats(bits, mu, sigma):
    x = np.array([int(b) for b in bits[::-1]])
    return dict(
        tickers=[ASSETS[i] for i in range(len(ASSETS)) if x[i]],
        risk=float(x @ sigma @ x),
        ret=float(mu @ x),
    )


def _private_pick(weights, candidates, mu, sigma):
    best = None
    for s in candidates:
        st = _portfolio_stats(s, mu, sigma)
        score = weights[0] * st["risk"] - weights[1] * st["ret"]
        if best is None or score < best[0]:
            best = (score, s, st)
    return best[2]


def payload_reader(vec, mu, sigma):
    """Attacker who knows the public market data and the algorithm and reads the parameter values."""
    n = len(mu)
    pairs, J_r, h_r, h_m = _coefficients(mu, sigma)
    A = np.concatenate([2 * GAMMA * h_r, 2 * GAMMA * J_r])
    B = np.concatenate([2 * GAMMA * h_m, np.zeros(len(pairs))])
    y = np.asarray(vec[:-1])
    coef, *_ = np.linalg.lstsq(np.stack([A, B], axis=1), y, rcond=None)
    resid = float(np.linalg.norm(np.stack([A, B], axis=1) @ coef - y))
    return (float(coef[0]), float(coef[1])), resid


def _nearest(w):
    return min(
        PREFERENCES,
        key=lambda k: np.hypot(PREFERENCES[k][0] - w[0], PREFERENCES[k][1] - w[1]),
    )


def portfolio_check(
    preference="risk_first", other="return_first", opt_level=2, transpile_seed=11
):
    if preference not in PREFERENCES or other not in PREFERENCES or preference == other:
        raise ValueError("choose two different preferences")
    started = time.perf_counter()
    mu, sigma, sha = load_market()
    tpl, params = portfolio_template()
    tc, _ = compilation.compile_circuit(tpl, opt_level, transpile_seed)
    sig = hashlib.sha256(
        json.dumps(
            [
                (i.operation.name, [tc.find_bit(q).index for q in i.qubits])
                for i in tc.data
            ]
        ).encode()
    ).hexdigest()[:16]
    w = PREFERENCES[preference]
    vec = bindings_for(w, mu, sigma)
    bound = _bind(tpl, params, vec)
    rec, resid = payload_reader(vec, mu, sigma)
    # the same template with another private preference: the compiled structure does not change
    vec_o = bindings_for(PREFERENCES[other], mu, sigma)
    cand, _ = defenses.apply_strategy(bound, "decomp+reorder", 3)
    v = verify(bound, cand)
    compiled_bound, _ = compilation.compile_circuit(bound, opt_level, transpile_seed)
    compiled_cand, _ = compilation.compile_circuit(cand, opt_level, transpile_seed)
    bm, cm = _metrics(compiled_bound), _metrics(compiled_cand)
    probabilities = Statevector(bound).probabilities()
    other_probabilities = Statevector(_bind(tpl, params, vec_o)).probabilities()
    compiled_verdict = _evidence(bound, compiled_cand)
    recovered = bool(np.allclose(rec, w, rtol=0, atol=1e-8) and resid < 1e-8)
    direct = dict(
        structure_hash=sig,
        structure_identical_across_preferences=True,
        structural_attacker_accuracy=1 / len(PREFERENCES),
        chance=1 / len(PREFERENCES),
        structural_accuracy_kind="analytical_uniform_prior_baseline_not_measured",
        payload_attacker=dict(
            recovered_weights=list(rec),
            true_weights=list(w),
            residual=resid,
            recovered_label=_nearest(rec),
            correct=recovered and _nearest(rec) == preference,
        ),
        payload_distinct_across_preferences=bool(np.linalg.norm(vec - vec_o) > 1e-9),
        rewrite=dict(
            strategy="decomp+reorder",
            verification=v.status,
            method=v.method,
            post_rewrite_payload_attack="not_implemented",
            compiled_verification=compiled_verdict,
            baseline_metrics=bm,
            metrics=cm,
            overhead={k: cm[k] / max(bm[k], 1) - 1 for k in ("depth", "n2q")},
            total_variation=float(
                np.abs(probabilities - Statevector(cand).probabilities()).sum() / 2
            ),
        ),
        circuit=_view(bound),
        candidate_circuit=_view(cand),
        bindings=vec.tolist(),
        feasible_probability=float(
            sum(p for i, p in enumerate(probabilities) if i.bit_count() == K)
        ),
        preference_distribution_tv=float(
            np.abs(probabilities - other_probabilities).sum() / 2
        ),
        attack_scope="Parameter reader tests the original logical template bindings, not the compiled job or rewritten bound circuit.",
        decision=dict(
            status=(
                "BLOCK"
                if recovered
                or v.status != "PASS"
                or compiled_verdict["status"] != "PASS"
                else "WARN"
            ),
            reasons=[
                (
                    "The original submitted bindings encode the private weights; the parameter reader recovers them."
                    if recovered
                    else "The parameter reader did not reconstruct the weights within tolerance; confidentiality is not established."
                ),
                "This tests the original logical bindings. Privacy after a bound-circuit rewrite is not measured.",
            ],
        ),
    )
    # fixed public sweep: the same three weight vectors are submitted for every analyst
    grid = list(PREFERENCES.values())

    def job(_private):
        vecs = [bindings_for(g, mu, sigma) for g in grid]
        return (
            hashlib.sha256(
                (
                    _circuit_hash(tpl)
                    + json.dumps([[float(x) for x in v_] for v_ in vecs])
                ).encode()
            ).hexdigest(),
            vecs,
        )

    ha, vecs = job(preference)
    hb, _ = job(other)
    cands = []
    sweep_checks = []
    for vv in vecs:
        job_circuit = _bind(tpl, params, vv)
        job_compiled, _ = compilation.compile_circuit(
            job_circuit, opt_level, transpile_seed
        )
        sweep_checks.append(_evidence(job_circuit, job_compiled))
        cands += _top_feasible(job_circuit)
    cands = list(dict.fromkeys(cands))
    everything = [format(v_, "08b") for v_ in range(256) if bin(v_).count("1") == K]

    def regret(wts, pick):
        sc = lambda st: wts[0] * st["risk"] - wts[1] * st["ret"]
        best = min(sc(_portfolio_stats(b, mu, sigma)) for b in everything)
        mean = float(np.mean([sc(_portfolio_stats(b, mu, sigma)) for b in everything]))
        return dict(regret_vs_best=sc(pick) - best, random_mean_regret=mean - best)

    sweep = dict(
        compiled_checks=sweep_checks,
        jobs=len(grid),
        job_hash_a=ha,
        job_hash_b=hb,
        identical=ha == hb,
        picks={
            k_: dict(
                **_private_pick(PREFERENCES[k_], cands, mu, sigma),
                **regret(
                    PREFERENCES[k_], _private_pick(PREFERENCES[k_], cands, mu, sigma)
                ),
            )
            for k_ in (preference, other)
        },
        distinct_candidates=len(cands),
        attacker_accuracy=1 / len(PREFERENCES),
        attacker_accuracy_kind="analytical_uniform_prior_baseline_not_measured",
        decision=dict(
            status=(
                "WARN"
                if ha == hb and all(c["status"] == "PASS" for c in sweep_checks)
                else "BLOCK"
            ),
            reasons=[
                (
                    "The logical job representation no longer depends on the private preference."
                    if ha == hb
                    else "Public job representations differ."
                ),
                (
                    "All public sweep circuits passed compiled equivalence."
                    if all(c["status"] == "PASS" for c in sweep_checks)
                    else "At least one public sweep circuit lacks a compiled equivalence PASS; no release is eligible."
                ),
                "The asset universe, the market-data Hamiltonian and the candidate set are still visible.",
                f"Costs {len(grid)} circuit runs instead of 1.",
            ],
        ),
    )
    return dict(
        elapsed_seconds=time.perf_counter() - started,
        workload=dict(
            circuit=_view(tpl),
            model="risk * x^T Sigma x - return * mu^T x",
            preparation="Fixed-weight basis state, XY preparation, cost phase, XY mixer",
            classical_feasible_count=len(everything),
            asset_rows=[
                dict(
                    ticker=a, expected_return=float(mu[i]), variance=float(sigma[i, i])
                )
                for i, a in enumerate(ASSETS)
            ],
        ),
        data=dict(
            source=DATA_URL,
            sha256=sha,
            assets=ASSETS,
            k=K,
            note="Public market snapshot from the Qiskit documentation; preferences are synthetic.",
        ),
        preference=preference,
        other=other,
        weights=PREFERENCES,
        direct=direct,
        sweep=sweep,
        scope=[
            "Eight assets and four held: small enough to simulate exactly, not a production portfolio.",
            "Preference recovery is a parameter-reading baseline, not a trained classifier. Chance rates are analytical under uniform priors, not measured classifier accuracy.",
            "Fixed sweep hashes cover the logical template and bindings only, not credentials, timing, transport or a Runtime job.",
            "Exact statevector probabilities select the top six feasible strings per public weight; this is not finite-shot sampling or a trained QAOA optimizer.",
            "Private preferences and toy predicates are sent to the local FastAPI server; deploy locally for the demonstrated trust boundary.",
            "Rewrite verification is on the bound logical circuit.",
            "Noiseless simulation; no hardware results and no claim of quantum advantage.",
        ],
    )
