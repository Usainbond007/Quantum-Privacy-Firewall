"""M5: adaptive attackers retrained on protected training groups, evaluated on the frozen protected test split."""
from _common import cli, pipeline
cfg = cli(__doc__); pipeline.evaluate_adaptive(cfg); print(pipeline.summary_text(cfg))
