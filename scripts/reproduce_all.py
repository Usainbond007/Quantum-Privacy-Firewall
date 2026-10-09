"""Run M0-M5 end to end and enforce the release gate. One command."""
from _common import cli, pipeline
import json, time
cfg = cli(__doc__); t = time.time()
pipeline.environment_snapshot(cfg); pipeline.build_manifest(cfg)
pipeline.train_baseline(cfg); pipeline.run_defense(cfg); pipeline.evaluate_adaptive(cfg)
print("\n" + pipeline.summary_text(cfg))
g = pipeline.release_gate(cfg); print("\nRELEASE GATE:", json.dumps(g, indent=2))
print(f"total {time.time() - t:.0f}s; artifacts in artifacts/{cfg['profile']}/")
raise SystemExit(0 if all(g.values()) else 1)
