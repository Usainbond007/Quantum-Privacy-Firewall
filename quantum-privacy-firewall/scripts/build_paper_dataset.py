import sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from qpf import paper_benchmark as PB
ap = argparse.ArgumentParser(); ap.add_argument("--profile", default="quick", choices=["smoke", "quick", "full"]); ap.add_argument("--workers", type=int, default=2)
a = ap.parse_args(); cfg = PB.load_cfg(a.profile); df = PB.build_dataset(cfg, a.workers)
print("rows", len(df), "sources", df.source_id.nunique(), "-> artifacts/paper_%s/features/dataset.csv" % a.profile)
