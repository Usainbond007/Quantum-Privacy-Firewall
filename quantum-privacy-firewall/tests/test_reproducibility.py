import pandas as pd
from qpf import config, pipeline, circuits

def _job(cfg, strategy="decomp+layout"):
    b = type("B", (), dict(base_id="qaoa-w6-000", family="qaoa", width=6, gen_seed=123))
    return pipeline._job(cfg, b, strategy, 42, [0, 2])

def test_run_job_repeats_exactly():
    cfg = config.load("smoke"); j = _job(cfg)
    a, b = pd.DataFrame(pipeline.run_job(j)), pd.DataFrame(pipeline.run_job(j))
    drop = ["compile_time_s", "verify_time_s"]
    pd.testing.assert_frame_equal(a.drop(columns=drop), b.drop(columns=drop))

def test_circuit_generators_are_pure_functions_of_seed():
    for f in list(circuits.FAMILIES) + [circuits.CONTROL]:
        assert circuits.make_circuit(f, 6, 9) == circuits.make_circuit(f, 6, 9)
        assert circuits.make_circuit(f, 6, 9) != circuits.make_circuit(f, 6, 10)

def test_backend_target_available():
    from qpf import compilation
    info = compilation.backend_info(); assert info["num_qubits"] == 120 and {"cz", "rz", "sx", "x"} <= set(info["operations"])
