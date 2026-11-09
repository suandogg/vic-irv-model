"""Run one paired candidate-field scenario from a saved release's exact inputs.

Usage: python tools/run_candidate_field_comparison.py RUN_DIR OUT_DIR SCENARIO DRAWS [DONOR_SET] [DROP_IDS]
DROP_IDS is a comma-separated list of candidate_ids run without a reviewed strength.
SCENARIO: control | retained (residual stays minor) | released (residual goes to
parties) | split (keeps separate IND and OTH targets; diagnostic only).
Copy this checkout's changed files over the restored inputs before running.
"""
import json
import os
import sys
import time
from pathlib import Path

SCENARIOS = {'control': None, 'retained': (1., 'combined'), 'released': (0., 'combined'),
             'split': (1., 'separate')}


def main(run, out, scenario, draws, donor_set='pooled', drop=''):
    run, out = Path(run).resolve(), Path(out).resolve()
    manifest = json.loads((run/'manifest.json').read_text())
    os.chdir(sys.path[0] if (Path(sys.path[0])/'SRC').exists() else '.')
    sys.path.insert(0, os.getcwd())
    sys.dont_write_bytecode = True
    import pandas as pd
    import SRC.forecast_engine as engine
    from SRC.constants import PARTIES
    from SRC.candidate_field import apply_candidate_field, load_field_config
    from SRC.irv import run_irv_for_district, district_key
    from SRC.primary_pipeline import build_projected_primaries, params_for_scenario
    sys.path.insert(0, str(Path(os.environ['ADAPTER_DIR'])))
    from trial_adapter import load_trial
    n, primary, matrices, params, posterior, ideology, adjustments = load_trial(Path('app.py').read_text())
    settings = dict(manifest['settings'], SIMULATIONS=int(draws))
    experiment = dict(manifest['experiment'])
    targets = manifest['targets']
    config = None
    if SCENARIOS[scenario]:
        retention, mode = SCENARIOS[scenario]
        config = load_field_config(retention, mode, donor_set)
        dropped = {x for x in drop.split(',') if x}
        if dropped - {c['candidate_id'] for c in config['candidates']}:
            raise ValueError('Unknown candidate to drop')
        config['candidates'] = [c for c in config['candidates'] if c['candidate_id'] not in dropped]
        experiment['candidate_field'] = config
    groups = manifest['subregions']
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    def progress(done, total):
        if done % 500 == 0 or done == total:
            print(f'{scenario} {done}/{total}: {time.monotonic()-started:.0f}s', flush=True)
    result = engine.simulate(primary, matrices, params, posterior, ideology, targets, adjustments,
                             settings, progress, experiment=experiment, subregions=groups)
    for key in ['seats', 'parties', 'government', 'draws', 'primary_draws']:
        result[key].to_csv(out/(key+'.csv'), index=False)
    central, _ = build_projected_primaries(primary, params, targets, adjustments, collect_diagnostics=False)
    summary = {}
    if config:
        central = apply_candidate_field(central, targets, config)
        summary = central.attrs['candidate_field']
    scoped = params_for_scenario(params, targets)
    rows = []
    for seat in central.to_dict('records'):
        votes = {p: float(seat[p]) for p in PARTIES}
        counted = run_irv_for_district(district_votes=votes, matrix=matrices[district_key(seat['district'])]['matrix'],
                                       seat_type=seat['seat_type'], params=scoped, posterior=posterior, ideology=ideology)
        rows.append(dict(district=seat['district'], **{p: 100*votes[p] for p in PARTIES},
                         winner=counted['winner'], runner_up=counted['runner_up'],
                         winner_pct=100*counted['winner_pct'], order='>'.join(counted['elimination_order'])))
    pd.DataFrame(rows).to_csv(out/'central.csv', index=False)
    (out/'summary.json').write_text(json.dumps(dict(summary, scenario=scenario, draws=int(draws),
                                                    donor_set=donor_set, dropped=drop, seconds=time.monotonic()-started,
                                                    roster=(config or {}).get('roster_status')), indent=2))


if __name__ == '__main__':
    main(*sys.argv[1:])
