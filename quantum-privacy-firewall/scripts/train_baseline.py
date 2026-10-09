"""M2: baseline leakage experiment (Random Forest + controls + transfer + repeated grouped splits)."""
from _common import cli, pipeline
import json
cfg = cli(__doc__); r = pipeline.train_baseline(cfg)
print(f"chance={r['chance']:.2f}  full={r['full']['macro_f1']:.3f}  shuffled={r['shuffled']['macro_f1']:.3f}  metadata-only={r['metadata_only']['macro_f1']:.3f}")
print("repeated grouped splits:", {k: f"{v['mean']:.3f}+/-{v['std']:.3f}" for k, v in r["repeated_grouped"].items()})
print("random-control circuits are predicted as:", r["random_control_predictions"])
print("EXIT GATE M2:", json.dumps(r["exit_gate"]))
