import sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
from qpf import paper_benchmark as PB
ap = argparse.ArgumentParser(); ap.add_argument("--profile", default="quick", choices=["smoke", "quick", "full"])
a = ap.parse_args(); cfg = PB.load_cfg(a.profile)
df = pd.read_csv(PB.out_dir(cfg, "features") / "dataset.csv"); df = df[df.status == "OK"].reset_index(drop=True)
res = PB.evaluate(cfg, df, tag="paper-features")                                   # Table II features, default conventions
res_used = PB.evaluate(cfg, df, feat_cols=PB.FEAT_USED, tag="gini-used-sensitivity")   # convention sensitivity
res["sensitivity_gini_used"] = res_used["summary"]
PB.jdump(res, PB.out_dir(cfg, "results") / "paper_benchmark.json")
import qpf.paper_compare as PCmp; PCmp.write_report(cfg, res)
