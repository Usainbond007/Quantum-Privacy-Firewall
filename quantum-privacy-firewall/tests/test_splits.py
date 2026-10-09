import pandas as pd
from qpf import config, pipeline

def test_grouped_split_disjoint_and_stratified():
    d = config.load("quick")["dataset"]; rows = [dict(base_id=f"{f}-{i}", family=f) for f in d["families"] + [d["control_family"]] for i in range(10)]
    m = pd.DataFrame(rows); m["split"] = m.base_id.map(pipeline.assign_splits(m, d["split"], 7))
    pipeline.check_disjoint(m)
    for f, g in m.groupby("family"): assert g.split.value_counts().to_dict() == {"train": 6, "val": 2, "test": 2}

def test_split_is_deterministic_and_seed_sensitive():
    m = pd.DataFrame([dict(base_id=f"a-{i}", family="a") for i in range(10)])
    s = lambda seed: pipeline.assign_splits(m, {"train": .6, "val": .2, "test": .2}, seed)
    assert s(1).equals(s(1)) and not s(1).equals(s(2))
