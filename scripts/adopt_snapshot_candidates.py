"""Explicit opt-in adoption of archived candidate CSV.
This verifies shape, keys and statuses only; NOT semantic correctness.
Must be followed by independent verification/tests in a Qiskit environment.
"""
from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from qpf import paper_benchmark as PB, paper_circuits as PC, paper_defense as PD, defenses, verification, compilation
from qpf.artifact_integrity import provenance, write_json_atomic
p=ROOT/'artifacts/paper_full/defense/candidates.csv'
df=pd.read_csv(p)
cfg=PB.load_cfg('full');d=cfg['defense']
expected=47*cfg['variants']*len(d['strategies'])*len(d['opt_levels'])
if len(df)!=expected or df.duplicated(['cid','opt']).any() or set(df.opt.astype(int))!=set(d['opt_levels']):
    raise SystemExit('REFUSED: candidate dataset shape/keys do not match expected snapshot')
if not set(df.verify_status.dropna()).issubset({'PASS','FAIL','UNKNOWN','ERROR'}):
    raise SystemExit('REFUSED: unknown verification status in cache')
print('WARNING: this only checks recorded statuses; it does not independently prove equivalence.')
expected_manifest=provenance(cfg,[PD.__file__,PC.__file__,defenses.__file__,verification.__file__,compilation.__file__],{'kind':'defense_candidates'})
write_json_atomic(p.with_suffix('.provenance.json'),expected_manifest)
print('Candidate cache adopted as SNAPSHOT EVIDENCE; rerun verification on representative samples before making claims.')
