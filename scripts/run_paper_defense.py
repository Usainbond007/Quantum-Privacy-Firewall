import sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
from qpf import paper_benchmark as PB, paper_defense as PD, paper_circuits as PC, compilation, defenses, verification
from qpf.artifact_integrity import provenance, require_matching_cache
ap = argparse.ArgumentParser(); ap.add_argument("--profile", default="quick", choices=["smoke", "quick", "full"]); ap.add_argument("--workers", type=int, default=2)
ap.add_argument("--reuse-candidates", action="store_true")
a = ap.parse_args(); cfg = PB.load_cfg(a.profile)
dp = PB.out_dir(cfg, "features") / "dataset.csv"
require_matching_cache(dp.with_suffix(".provenance.json"), provenance(cfg, [PC.__file__, PB.__file__, compilation.__file__, PB.ROOT / "src/qpf/paper_features.py"], {"kind": "paper_dataset"}))
ds = pd.read_csv(dp); ds = ds[ds.status == "OK"].reset_index(drop=True)
cp = PB.out_dir(cfg, "defense") / "candidates.csv"
if a.reuse_candidates and cp.exists():
    require_matching_cache(cp.with_suffix(".provenance.json"), provenance(cfg, [PD.__file__, PC.__file__, defenses.__file__, verification.__file__, compilation.__file__], {"kind": "defense_candidates"}))
    cands = pd.read_csv(cp)
else:
    cands = PD.build_candidates(cfg, a.workers)
res = PD.evaluate_defense(cfg, ds, cands, workers=a.workers); PB.jdump(res, PB.out_dir(cfg, "results") / "paper_defense.json")
print(PD.write_defense_report(cfg, res).read_text())
