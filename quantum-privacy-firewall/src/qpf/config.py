import pathlib, yaml
ROOT = pathlib.Path(__file__).resolve().parents[2]

def load(profile="quick"):
    cfg = {"profile": profile}
    for name in ("dataset", "backend", "experiment", "budgets"):
        d = yaml.safe_load(open(ROOT / "config" / f"{name}.yaml"))
        d.update(d.pop("profiles", {}).get(profile, {}))
        cfg[name] = d
    return cfg

def art(cfg, sub):
    p = ROOT / "artifacts" / cfg["profile"] / sub
    p.mkdir(parents=True, exist_ok=True)
    return p
