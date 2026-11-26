from pathlib import Path
import json
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]
at=AppTest.from_file(str(ROOT/'snapshot_app.py'),default_timeout=120).run()
next(x for x in at.radio if x.label=='View').set_value('Legislative Assembly').run()
next(x for x in at.radio if x.label=='Results view').set_value('Seat Detail').run()
next(x for x in at.selectbox if x.label=='Select district to inspect IRV count').set_value('Werribee').run()
assert not at.exception and not at.error,[x.value for x in at.exception]
assert any('Werribee named-candidate count' in x.value for x in at.subheader)
frame=next(x.value for x in at.dataframe if 'candidate_id' in x.value.columns)
assert 'OTH' not in set(frame.candidate_id),frame
names=set(frame.candidate_id)-{'ALP','LNP','GRN','ON','IND'}
assert len(names)==5,names
(ROOT/'reports/v7_engine_port_2026-11-26/werribee-local.json').write_text(json.dumps(dict(entrypoint='snapshot_app.py',pooled_OTH_candidate_present=False,separate_OTH_nominees=sorted(names),exceptions=[],errors=[]),indent=2)+'\n')
print('PASS: Werribee inspector uses five separate OTH nominees, no pooled OTH candidate')
