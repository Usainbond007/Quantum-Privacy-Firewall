"""Write artifacts/<profile>/results_summary.txt from saved artifacts (no hand-typed numbers)."""
from _common import cli, pipeline
from qpf.config import art
cfg = cli(__doc__); t = pipeline.summary_text(cfg); (art(cfg, "results") / "results_summary.txt").write_text(t + "\n"); print(t)
