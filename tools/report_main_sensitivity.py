"""Reproduce Main comparisons using committed inputs, never live-sheet writes.

Loads the actual app's run_model function from its AST (without running UI or
sync), so primary construction cannot drift from Main's production pipeline.
"""
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from SRC.preference_sensitivity import compare, assumption_rows


def main():
    tree = ast.parse((ROOT/'app.py').read_text())
    selected = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
                or isinstance(node, ast.FunctionDef) and node.name in ('run_model','params_for_scenario')]
    namespace = {'__file__': str(ROOT/'app.py'), 'log_checkpoint': lambda *args: None}
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(ROOT/'app.py'),'exec'),namespace)
    n = namespace
    params = n['load_params']()
    primary_inputs = n['apply_seat_held_metadata'](n['load_legacy_primary_inputs'](),n['load_seat_held_metadata']())
    matrices = n['attach_vec_fields'](n['rebuild_oth_matrices'](n['load_synth_pref_matrices'](),params))
    posterior = n['apply_production_federal_on_evidence'](n['load_posterior_scenarios']())
    ideology = n['load_ideology_prior']()
    adjustments = n['load_lower_seat_adjustments']()
    out = ROOT/'reports/main_sensitivity_2026_10_10'
    out.mkdir(exist_ok=True)
    for label,on,minor in [('central',22,5.5),('lower_on',19,7),('higher_on',25,4)]:
        targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=on,IND=minor,OTH=minor)
        expected, adjusted, _ = n['run_model'](primary_inputs,matrices,params,posterior,ideology,targets,adjustments)
        primary = n['build_primary_vote_table'](adjusted)
        scenario_params = n['params_for_scenario'](params,targets)
        summary, detail = compare(primary,matrices,scenario_params,posterior,ideology)
        actual = detail[detail.Configuration.eq('Central model')].set_index('district')
        reference = expected.set_index('district')
        assert actual.winner.equals(reference.winner)
        assert (actual.ALP_2PP-reference.ALP_2PP).abs().max() < 1e-12
        assert all(summary[['ALP','LNP','GRN','ON','IND','OTH']].sum(axis=1).eq(88))
        summary.to_csv(out/f'{label}_summary.csv',index=False)
        detail.to_csv(out/f'{label}_seats.csv',index=False)
        affected = sorted(detail.loc[detail['Winner changed'],'district'].unique())
        audits = [assumption_rows(primary,matrices,scenario_params,posterior,ideology,seat) for seat in affected]
        if audits:
            n['pd'].concat(audits,ignore_index=True).to_csv(out/f'{label}_consequential_assumptions.csv',index=False)
        print(label, summary.to_string(index=False), 'Affected: '+', '.join(affected), sep='\n')
    files = sorted((ROOT/'data').rglob('*.csv'))
    manifest = {'input_mode':'committed CSV snapshot, not live Google Sheets',
                'date':'2026-10-10', 'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))


if __name__ == '__main__':
    main()
