import sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from qpf import config, pipeline

def cli(desc):
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--profile", default="quick", choices=["smoke", "quick", "full"])
    ap.add_argument("--workers", type=int, default=None, help="parallel worker processes (default from config)")
    a = ap.parse_args(); cfg = config.load(a.profile)
    if a.workers: cfg["experiment"]["workers"] = a.workers
    return cfg
