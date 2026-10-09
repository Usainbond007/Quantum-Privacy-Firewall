"""One-time adoption of the snapshot dataset whose SHA256 is recorded in HANDOFF.md.
Only the dataset can be adopted; candidate artifacts are NOT attested by this script.
"""
from pathlib import Path
import sys, hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from qpf import paper_benchmark as PB, paper_circuits as PC, compilation
from qpf.artifact_integrity import provenance, write_json_atomic
p=ROOT/'artifacts/paper_full/features/dataset.csv'
known='a3d5f34bf93ab32f'
actual=hashlib.sha256(p.read_bytes()).hexdigest()
if not actual.startswith(known):
    raise SystemExit('REFUSED: dataset SHA256 differs from the handoff recorded value')
import pandas as pd
df=pd.read_csv(p)
if len(df)!=2256 or df.source_id.nunique()!=282 or (df.status!='OK').any() or df.duplicated(['generator','variant','n_qubits','opt']).any():
    raise SystemExit('REFUSED: dataset shape/status/keys do not match snapshot')
cfg=PB.load_cfg('full')
expected=provenance(cfg,[PC.__file__,PB.__file__,compilation.__file__,ROOT/'src/qpf/paper_features.py'],{'kind':'paper_dataset'})
write_json_atomic(p.with_suffix('.provenance.json'),expected)
print('ADOPTED dataset from exact recorded SHA256; this does NOT independently verify generator semantics or features.')
