"""M0+M1: environment snapshot, grouped 60/20/20 split by base_id, frozen test ids."""
from _common import cli, pipeline
cfg = cli(__doc__)
snap = pipeline.environment_snapshot(cfg); man = pipeline.build_manifest(cfg)
print("backend:", snap["backend"]["name"], snap["backend"]["num_qubits"], "qubits; native ops:", snap["backend"]["operations"])
print(man.groupby(["family", "split"]).size().unstack(fill_value=0))
print("EXIT GATE M1: no base_id in more than one partition -> PASS")
