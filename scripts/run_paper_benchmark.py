import sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
from qpf import paper_benchmark as PB, paper_circuits as PC, compilation
from qpf.artifact_integrity import provenance, require_matching_cache
ap = argparse.ArgumentParser(); ap.add_argument("--profile", default="quick", choices=["smoke", "quick", "full"])
a = ap.parse_args(); cfg = PB.load_cfg(a.profile)
dp = PB.out_dir(cfg, "features") / "dataset.csv"
require_matching_cache(dp.with_suffix(".provenance.json"), provenance(cfg, [PC.__file__, PB.__file__, compilation.__file__, PB.ROOT / "src/qpf/paper_features.py"], {"kind": "paper_dataset"}))
df = pd.read_csv(dp); df = df[df.status == "OK"].reset_index(drop=True)
res = PB.evaluate(cfg, df, tag="paper-features")                                   # Table II features, default conventions
res_used = PB.evaluate(cfg, df, feat_cols=PB.FEAT_USED, tag="gini-used-sensitivity")   # convention sensitivity
res["sensitivity_gini_used"] = res_used["summary"]
PB.jdump(res, PB.out_dir(cfg, "results") / "paper_benchmark.json")
import qpf.paper_compare as PCmp; PCmp.write_report(cfg, res)
