import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np

def confusion(cm, labels, title, path):
    cm = np.array(cm); fig, ax = plt.subplots(figsize=(5, 4.4)); ax.imshow(cm, cmap="Purples")
    ax.set_xticks(range(len(labels))); ax.set_yticks(range(len(labels))); ax.set_xticklabels(labels, rotation=30, ha="right"); ax.set_yticklabels(labels)
    for i in range(len(labels)):
        for j in range(len(labels)): ax.text(j, i, cm[i, j], ha="center", va="center", color="black" if cm[i, j] < cm.max() / 2 else "white")
    ax.set_xlabel("attacker's guess"); ax.set_ylabel("true family"); ax.set_title(title, fontsize=9); fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)

def frontier(res, path):
    xs, ys, ys2 = [], [], []
    for b, v in res["budgets"].items():
        xs.append(float(b) * 100); ys.append(v["attackers"]["adaptive_rf"]["macro_f1"])
        ys2.append(v["attackers"].get("adaptive_rf_normalization_aware", {}).get("macro_f1", np.nan))
    fig, ax = plt.subplots(figsize=(6, 4)); ax.plot(xs, ys, "o-", color="#7B4FD6", label="adaptive RF")
    ax.plot(xs, ys2, "s--", color="#FA7CB4", label="normalization-aware RF")
    ax.axhline(res["baseline_test_macro_f1"], color="k", ls=":", label="baseline (unprotected)")
    ax.axhline(res["chance"], color="gray", ls="--", label="chance")
    ax.set_xlabel("allowed relative overhead cap (%)"); ax.set_ylabel("attacker macro-F1 (lower = more private)")
    ax.set_title("Privacy-cost frontier (frozen test split)", fontsize=10); ax.legend(fontsize=8); ax.set_ylim(0, 1.05)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)
