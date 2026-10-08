"""Seat-held-out prediction of extracted category-origin flows on known fields.

Targets are reconstructed category-origin allocations, not literal transfers
from a single candidate's elimination parcel. This tests conditional shares,
not candidate elimination order, election outcomes, or high-ON behaviour.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_vec_field_holdout import pool_fields
from tools.trial_vec_field_evidence import attach_vec_fields
from tools.preference_review_trials import variant
from tools.validate_leave_one_out import mean_matrix
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.ideology_loader import load_ideology_prior
from SRC.preference_engine import diagnose_preference_weights


def distance(predicted, actual, field):
    # Half L1: percentage of flow mass assigned to different destinations.
    return 50*sum(abs(predicted.get(p, 0)-actual.get(p, 0)) for p in field)


def main(ablations=False):
    matrices = load_synth_pref_matrices()
    evidence = attach_vec_fields(matrices)
    params = load_params()
    params['scalar_params']['SCENARIO_ON_PRIMARY'] = 0
    ideology = load_ideology_prior()
    rows = []
    for seat, item in evidence.items():
        training = [v for k, v in matrices.items() if k != seat and v['seat_type'] == item['seat_type']]
        matrix = mean_matrix(training or [v for k, v in matrices.items() if k != seat])
        pools = {name: pool_fields(evidence, seat, restricted, minimum) for name, restricted, minimum in
                 [('all_min1', False, 1), ('all_min3', False, 3), ('all_min5', False, 5), ('class_min1', True, 1), ('class_min3', True, 3), ('class_min5', True, 5)]}
        for origin, target in item['matrix'].get('__vec_field_rows__', {}).items():
            field = target['field']
            if len(field) < 2:
                continue  # One destination is tautological, not predictive evidence.
            reference = diagnose_preference_weights(origin, field, matrix, item['seat_type'], params, {}, ideology)['final_flows']
            comparisons = pools
            if ablations:
                comparisons = {name: pools['all_min3'] for name in ['unchanged', 'no_non_on_geography', 'no_constraints', 'no_incomplete_anchor', 'no_geography_or_constraints', 'no_all_three', 'historical_only_coverage', 'historical_only_coverage_no_geography']}
            for name, pool in comparisons.items():
                record = pool.get(origin, {}).get('+'.join(field))
                if record is None:
                    continue  # Report coverage separately; matched-set comparisons only.
                assert seat not in record['training_seats']
                trial = copy.deepcopy(matrix)
                trial['__vec_pooled_fields__'] = pool
                if name.startswith('historical_only_coverage'):
                    # Diagnostic only: remove synthetic ON mass from a field
                    # where ON was absent, to isolate coverage-based selection.
                    trial.setdefault(origin, {})['ON'] = 0
                settings = variant(params, 'vec_exact_field')
                if name in ('no_non_on_geography', 'no_geography_or_constraints', 'no_all_three', 'historical_only_coverage_no_geography'):
                    settings = variant(settings, 'no_non_on_recipient_geography')
                if name in ('no_constraints', 'no_geography_or_constraints', 'no_all_three'):
                    settings = variant(settings, 'no_constraints')
                if name in ('no_incomplete_anchor', 'no_all_three'):
                    settings = variant(settings, 'no_incomplete_matrix_anchor')
                predicted = diagnose_preference_weights(origin, field, trial, item['seat_type'], settings, {}, ideology)['final_flows']
                rows.append({'seat': seat, 'origin': origin, 'field': '+'.join(field), 'variant': name,
                             'training_seats': len(record['training_seats']),
                             'reference_distance_pp': distance(reference, target['shares'], field),
                             'engine_distance_pp': distance(predicted, target['shares'], field),
                             'direct_pool_distance_pp': distance(record['shares'], target['shares'], field)})
    eligible = sum(len(r['field']) >= 2 for item in evidence.values() for r in item['matrix'].get('__vec_field_rows__', {}).values())
    summary = {}
    common_keys = None
    for name in comparisons:
        keys = {(r['seat'], r['origin'], r['field']) for r in rows if r['variant'] == name}
        common_keys = keys if common_keys is None else common_keys & keys
    for name in comparisons:
        selected = [r for r in rows if r['variant'] == name]
        summary[name] = {'matched_fields': len(selected), 'eligible_fields': eligible,
                         'reference_distance_pp': sum(r['reference_distance_pp'] for r in selected)/len(selected),
                         'engine_distance_pp': sum(r['engine_distance_pp'] for r in selected)/len(selected),
                         'direct_pool_distance_pp': sum(r['direct_pool_distance_pp'] for r in selected)/len(selected)}
        shared = [r for r in selected if (r['seat'], r['origin'], r['field']) in common_keys]
        summary[name]['all_variants_common_fields'] = len(shared)
        summary[name]['common_engine_distance_pp'] = sum(r['engine_distance_pp'] for r in shared)/len(shared)
        summary[name]['common_direct_pool_distance_pp'] = sum(r['direct_pool_distance_pp'] for r in shared)/len(shared)
    target = ROOT/'reports/preference_review_2026_10_08'/('vec_conditional_ablations.json' if ablations else 'vec_conditional_flows.json')
    target.write_text(json.dumps({'metric': 'Mean half-L1 flow-share distance in percentage points, equal weight per held-out category-field; each reference comparison uses identical matched fields.', 'summary': summary, 'fields': rows}, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main(ablations='--ablations' in sys.argv)
