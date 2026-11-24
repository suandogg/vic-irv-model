"""Restore the independently frozen website control into a temporary directory."""
import argparse,json,tarfile,hashlib,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--destination',type=Path,default=Path('/private/tmp/prism-v6-control'));a=p.parse_args()
ROOT=Path(__file__).resolve().parents[1];m=json.loads((a.run/'manifest.json').read_text());archive=a.run/'reproduction-inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==m['files'][archive.name]
assert m['targets']==json.loads((ROOT/'data/v6_targets.json').read_text())
sys.path.insert(0,str(ROOT/'reports/v6_engine_port_2026-11-25/reference'));import website_release_profile as w
assert m['website_release_profile']==w.profile_metadata()
a.destination.mkdir(exist_ok=False)
with tarfile.open(archive) as t:t.extractall(a.destination,filter='data')
w.apply_input_corrections(a.destination,w.V6_INPUT_CORRECTIONS)
print('Restored verified independent control:',a.destination)
