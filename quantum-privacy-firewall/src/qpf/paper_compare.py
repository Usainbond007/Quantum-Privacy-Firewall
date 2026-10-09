"""Side-by-side of OUR measured transfer matrices with the numbers the paper REPORTS (config/paper_reference.json).
Reference values live in their own file and are only read here, for display."""
import json, pathlib
from .paper_benchmark import out_dir, ROOT

def _cell(s): return "n/a" if not s else f"{s['mean']:.3f}±{s['std']:.3f}"

def _table(title, ours, ref, rows, cols, prefix_fmt):
    L = [f"### {title}", "", "Each cell: ours accuracy / macro-F1 (mean±std over splits) · paper accuracy / macro-F1.", "",
         "| train \\ test | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for a in rows:
        cells = []
        for b in cols:
            k = prefix_fmt(a, b); o = ours.get(k); r = ref.get(k)
            cells.append(f"{_cell(o['accuracy']) if o else 'n/a'} / {_cell(o['macro_f1']) if o else 'n/a'}<br>paper {r[0]:.3f} / {r[1]:.3f}" if r else "n/a")
        L.append(f"| {a} | " + " | ".join(cells) + " |")
    return L

def write_report(cfg, res, path=None):
    ref = json.load(open(ROOT / "config" / "paper_reference.json")); S = res["summary"]
    Lv = [f"L{o}" for o in cfg["opt_levels"]]; L = ["# Paper-aligned benchmark: measured vs reported", "",
        "Independent implementation. Generators, feature conventions and dataset size are our interpretation; the paper does not publish them. "
        "Differences from the paper's numbers are therefore expected and are NOT evidence for or against the paper.", "",
        f"Profile `{cfg['profile']}`: {res['n_sources']} source circuits, {res['n_rows']} transpiled circuits, {cfg['n_splits']} repeated source-disjoint splits, chance = {res['chance']:.3f}.", ""]
    L += _table("Optimization-level generalization (sizes pooled)", S["opt_transfer"], ref["opt_transfer_acc_f1"], Lv, Lv, lambda a, b: f"{a}->{b}"); L.append("")
    if S["size_transfer"]:
        sz = [f"{n}q" for n in cfg["sizes"]] + ["24+48"]; L += _table("Circuit-size generalization (optimization levels pooled)", S["size_transfer"], ref["size_transfer_acc_f1"], sz, sz, lambda a, b: f"{a}->{b}"); L.append("")
    L += ["### Controls and stricter checks (pooled test, mean±std)", "", "| setting | accuracy | macro-F1 |", "|---|---|---|"]
    for name, lab in (("pooled", "Table II features, source-disjoint (paper-style)"), ("control_shuffled_labels", "Shuffled-label control"),
                      ("control_metadata_only", "Unnormalized size metadata only (n_gates, depth, n2q, width)"),
                      ("generator_disjoint_pooled", "Generator-disjoint split (whole generators held out)")):
        L.append(f"| {lab} | {_cell(S[name]['accuracy'])} | {_cell(S[name]['macro_f1'])} |")
    if "sensitivity_gini_used" in res:
        u = res["sensitivity_gini_used"]; L.append(f"| Gini over used edges/qubits only (convention sensitivity) | {_cell(u['pooled']['accuracy'])} | {_cell(u['pooled']['macro_f1'])} |")
    p = pathlib.Path(path) if path else out_dir(cfg, "results") / "paper_comparison.md"; p.write_text("\n".join(L) + "\n"); return p
