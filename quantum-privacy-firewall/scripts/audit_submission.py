"""No-Qiskit evidence audit. Outputs JSON; never claims a security proof."""
import argparse, csv, json, hashlib
from pathlib import Path

def audit(root):
    root = Path(root)
    feat = root / 'artifacts/paper_full/features/dataset.csv'
    cand = root / 'artifacts/paper_full/defense/candidates.csv'
    result = root / 'artifacts/paper_full/results'
    out = {'research_claim': 'NOT ESTABLISHED', 'dataset': {}, 'defense_candidates': {}, 'benchmark': {}, 'defense': {}}
    if feat.exists():
        with feat.open(newline='') as f:
            reader = csv.DictReader(f)
            keys=set(); sources=set(); status={}; duplicates=0; count=0
            for r in reader:
                count+=1
                key=(r['generator'],r['variant'],r['n_qubits'],r['opt'])
                if key in keys: duplicates+=1
                keys.add(key); sources.add(r['source_id']); status[r['status']]=status.get(r['status'],0)+1
        out['dataset']={'rows':count,'sources':len(sources),'duplicates':duplicates,'statuses':status,'sha256':hashlib.sha256(feat.read_bytes()).hexdigest()}
    else: out['dataset']={'error':'missing'}
    if cand.exists():
        with cand.open(newline='') as f:
            reader=csv.DictReader(f); count=0; verdicts={}; keys=set(); duplicates=0
            for r in reader:
                count+=1; v=r.get('verify_status',''); verdicts[v]=verdicts.get(v,0)+1
                k=(r.get('cid'),r.get('opt'))
                if k in keys: duplicates+=1
                keys.add(k)
        out['defense_candidates']={'rows':count,'duplicate_candidate_opt':duplicates,'verification_statuses':verdicts}
    else: out['defense_candidates']={'error':'missing'}
    for key, name in [('benchmark','paper_benchmark.json'),('defense','paper_defense.json')]:
        path=result/name
        if path.exists():
            try:
                data=json.loads(path.read_text())
                out[key]={'present':True,'json_valid':True,'top_level_keys':list(data)[:20]}
            except (ValueError, UnicodeError) as e: out[key]={'present':True,'json_valid':False,'error':str(e)}
        else: out[key]={'present':False}
    out['engineering_evidence_complete']= bool(out['benchmark'].get('json_valid') and out['defense'].get('json_valid') and out['dataset'].get('duplicates')==0 and out['dataset'].get('statuses',{}).get('ERROR',0)==0)
    out['scientific_privacy_result']='NOT EVALUATED BY THIS AUDIT; requires held-out adaptive and normalization-aware evaluation'
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--output')
    a=p.parse_args();res=audit(a.root);print(json.dumps(res,indent=2))
    if a.output: Path(a.output).write_text(json.dumps(res,indent=2)+'\n')
