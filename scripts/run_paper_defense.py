import sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
from qpf import paper_benchmark as PB, paper_defense as PD
ap = argparse.ArgumentParser(); ap.add_argument("--profile", default="quick", choices=["smoke", "quick", "full"]); ap.add_argument("--workers", type=int, default=2)
ap.add_argument("--reuse-candidates", action="store_true")
a = ap.parse_args(); cfg = PB.load_cfg(a.profile)
ds = pd.read_csv(PB.out_dir(cfg, "features") / "dataset.csv"); ds = ds[ds.status == "OK"].reset_index(drop=True)
cp = PB.out_dir(cfg, "defense") / "candidates.csv"
cands = pd.read_csv(cp) if (a.reuse_candidates and cp.exists()) else PD.build_candidates(cfg, a.workers)
res = PD.evaluate_defense(cfg, ds, cands, workers=a.workers); PB.jdump(res, PB.out_dir(cfg, "results") / "paper_defense.json")
print(PD.write_defense_report(cfg, res).read_text())
