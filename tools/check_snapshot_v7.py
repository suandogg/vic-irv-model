"""Exercise the deployed entrypoint with Streamlit AppTest, not app.py directly."""
from pathlib import Path
import json
import pandas as pd
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports/v7_engine_port_2026-11-26'
at=AppTest.from_file(str(ROOT/'snapshot_app.py'),default_timeout=120).run()
assert not at.exception and not at.error,[x.value for x in at.exception]
assert {x.label:float(x.value) for x in at.number_input}==json.loads((ROOT/'data/v7_targets.json').read_text())
flags={x.key:x.value for x in at.checkbox};assert all(flags.get(k) is True for k in ('candidate_field_version_b','alp_low_base_taper','oth_proportional','htv_deal_2026','htv_review_2026'))
next(x for x in at.radio if x.label=='View').set_value('Legislative Assembly').run();assert not at.exception and not at.error
frame=next(x.value for x in at.dataframe if len(x.value)==88 and 'Winner 2CP %' in x.value.columns).set_index('district')
expected=pd.read_csv(R/'native/central.csv').set_index('district');checks={}
for seat in ('Werribee','Hawthorn','Ripon','Narracan','Ringwood','South Barwon'):
 a=frame.loc[seat];b=expected.loc[seat];assert a.winner==b.winner and a.runner_up==b.runner_up,(seat,a,b)
 assert abs(float(a['Winner 2CP %'])-100*float(b.winner_pct))<.0051,(seat,a['Winner 2CP %'],b.winner_pct)
 checks[seat]={'winner':a.winner,'runner_up':a.runner_up,'displayed_winner_pct':float(a['Winner 2CP %'])}
assert any('v7' in x.value for x in at.caption)
print('RADIOS BEFORE',[(x.label,x.value,x.options) for x in at.radio]); view=next(x for x in at.radio if x.label=='View');view.set_value(view.options[-1]).run();print('RADIOS AFTER',[(x.label,x.value) for x in at.radio]);print('SELECTS AFTER',[(x.label,x.value) for x in at.selectbox]);assert not at.exception and not at.error,[x.value for x in at.exception]
choices={x.label:x.value for x in at.selectbox};assert choices['Structural uncertainty trial (unvalidated)']=='Concentration + structured nowcast (development)';assert choices['Geographic uncertainty grouping']=='Blend upper-house and sub-regions';assert choices['Concentration mapping (research)']=='Positive bounded (0–2)'
(R/'streamlit-checks.json').write_text(json.dumps({'entrypoint':'snapshot_app.py','exceptions':[],'errors':[],'target_defaults':json.loads((ROOT/'data/v7_targets.json').read_text()),'checked_seats':checks,'forecast_defaults':choices},indent=2)+'\n');print('PASS: snapshot_app.py targets, mandatory final-profile switches, five seat results and forecast defaults.')
