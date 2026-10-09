"""M3+M4: generate candidates, verify equivalence, compile, enforce budgets, label-free selection."""
from _common import cli, pipeline
import json
cfg = cli(__doc__); s = pipeline.run_defense(cfg)
print("verification:", s["verification_counts"], "| methods:", s["verification_method_counts"])
print("survival rate (candidate features differ from baseline), by strategy:")
for k, v in s["survival_rate_by_strategy"].items(): print(f"   {k:24s} {v['mean']:.2f}  (n={int(v['count'])})")
print("selection:", json.dumps(s["selection"]))
