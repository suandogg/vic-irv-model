"""Compare all written precision and all observed seat/draw values, without tolerances."""
from pathlib import Path
import json,hashlib,numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1]/'reports/v7_engine_port_2026-11-26'
a=R/'reference';b=R/'native';checks={}
for f in ('central.csv','primaries.csv','scenario-b-central.csv','scenario-b-primaries.csv','seats.csv','parties.csv','draws.csv','government.csv','primary_draws.csv','final_pairs.csv'):
 checks[f]=(a/f).read_bytes()==(b/f).read_bytes()
x=np.load(a/'per_draw.npz');y=np.load(b/'per_draw.npz')
for k in x.files:checks['array:'+k]=np.array_equal(x[k],y[k])
seats=pd.read_csv(a/'primaries.csv').district.to_list();different=[]
for i,seat in enumerate(seats):
 if any(not np.array_equal(x[k][:,i],y[k][:,i]) for k in ('primary','winner','margin','alp_2pp')):different.append(seat)
pairs_a=pd.read_csv(a/'final_pairs.csv');pairs_b=pd.read_csv(b/'final_pairs.csv');assert len(pairs_a)==88000
summary={'checks':checks,'different_seats':different,'draws':1000,'seed':20261010,'python_hash_seed':0,'per_seat_draws':88000,'passed':all(checks.values()) and not different}
root=R.parents[1]
paths=sorted((root/'SRC').glob('*.py'))+sorted((root/'data/raw').glob('*'))+sorted((root/'data/development').rglob('*.csv'))+[root/n for n in ('app.py','snapshot_app.py','requirements.txt','data/v7_targets.json','data/v6_protected_inputs.json')]
summary['native_source_and_input_sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
(R/'exact_match.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));assert summary['passed']
