"""Fixed-primary activation inventory and Ringwood preference-only trace."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.preference_review_trials import SCENARIOS, variant
from tools.compare_latent_ranking_shadow import build_primaries
from tools.trial_vec_field_evidence import attach_vec_fields
from SRC.params_loader import load_params
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.ideology_loader import load_ideology_prior
from SRC.posterior_loader import load_posterior_scenarios
from SRC.federal_on_evidence_loader import apply_production_federal_on_evidence
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.seat_adjustments_loader import load_lower_seat_adjustments
from SRC.irv import trace_irv_for_district, trace_preference_diagnostics_for_district, initialise_parcels, parcel_totals, distribute_parcel_holder
from SRC.preference_engine import diagnose_preference_weights
from SRC.constants import PARTIES


def audit_origins(votes, matrix, seat_type, settings, post, ideology):
    parcels = initialise_parcels(votes)
    alive = [p for p in PARTIES if votes.get(p, 0) > 0]
    records = []
    protected_checks = 0
    while len(alive) > 2:
        totals = parcel_totals(parcels)
        holder = min(alive, key=lambda p: totals[p])
        remaining = [p for p in alive if p != holder]
        holder_diag = diagnose_preference_weights(holder, remaining, matrix, seat_type, settings, post, ideology)
        special = holder_diag['basis'] == 'ON special prior'
        for origin, amount in parcels[holder].items():
            if amount <= 0:
                continue
            lookup = holder if origin == holder or special else origin
            corrected = diagnose_preference_weights(lookup, remaining, matrix, seat_type, settings, post, ideology)
            original_settings = variant(settings, 'vec_exact_field')
            original_settings['scalar_params']['TRIAL_VEC_FIELD_COVERAGE'] = False
            original = diagnose_preference_weights(lookup, remaining, matrix, seat_type, original_settings, post, ideology)
            if special or 'ON' in remaining:
                assert corrected['final_flows'] == original['final_flows'], (holder, origin, remaining)
                protected_checks += 1
            if corrected['stages'][0].get('vec_field_coverage_corrected'):
                delta = {p: corrected['final_flows'].get(p, 0)-original['final_flows'].get(p, 0) for p in remaining}
                records.append({'holder': holder, 'origin': origin, 'lookup': lookup, 'votes': amount,
                                'alive': remaining, 'flow_delta_pp': {p: v*100 for p, v in delta.items()},
                                'consequential': any(abs(v) > 1e-12 for v in delta.values())})
        distribute_parcel_holder(parcels, holder, remaining, matrix, seat_type, settings, post, ideology)
        alive = remaining
    return records, protected_checks


def main():
    params = load_params()
    inputs = load_legacy_primary_inputs()
    matrices = load_synth_pref_matrices()
    attached = attach_vec_fields(matrices)
    post = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    adjustments = load_lower_seat_adjustments()
    activations, traces, ringwood_diagnostics, origin_activations = [], {}, {}, []
    protected_checks = 0
    for scenario, targets in SCENARIOS.items():
        primary, settings = build_primaries(inputs, params, targets, adjustments)
        for district, group in primary.groupby('district'):
            seat = str(district).upper()
            item = attached[seat]
            values = group.set_index('party').primary_vote.to_dict()
            votes = {p: float(values.get(p, 0)) for p in PARTIES}
            corrected = variant(settings, 'vec_field_coverage')
            origins, checked = audit_origins(votes, item['matrix'], item['seat_type'], corrected, post, ideology)
            origin_activations.extend(dict(scenario=scenario, seat=seat, **r) for r in origins)
            protected_checks += checked
            stages = trace_preference_diagnostics_for_district(votes, item['matrix'], item['seat_type'], corrected, post, ideology)
            for stage in stages:
                if stage.get('vec_field_coverage_corrected'):
                    activations.append({'scenario': scenario, 'seat': seat, 'round': stage['round'], 'eliminated': stage['eliminated'], 'alive': stage['alive'], 'coverage': stage['aec_coverage']})
            if seat == 'RINGWOOD':
                ringwood_diagnostics[scenario] = stages
                traces[scenario] = {}
                for name in ('reference', 'vec_exact_field', 'vec_field_coverage'):
                    matrix = matrices[seat]['matrix'] if name == 'reference' else item['matrix']
                    traces[scenario][name] = trace_irv_for_district(votes, matrix, item['seat_type'], variant(settings, name), post, ideology)
    summary = {s: {'corrected_holder_rounds': sum(a['scenario'] == s for a in activations), 'affected_seats': len({a['seat'] for a in activations if a['scenario'] == s})} for s in SCENARIOS}
    origin_summary = {s: {'corrected_parcels': sum(r['scenario'] == s for r in origin_activations), 'consequential_parcels': sum(r['scenario'] == s and r['consequential'] for r in origin_activations), 'ON_held_corrected_parcels': sum(r['scenario'] == s and r['holder'] == 'ON' for r in origin_activations)} for s in SCENARIOS}
    payload = {'scope': 'Actual contest diagnostics; excludes forced 2PP runs. Holder and primary-origin activation inventories are separate.', 'summary': summary, 'origin_summary': origin_summary, 'protected_flow_equality_checks': protected_checks, 'origin_activations': origin_activations, 'activations': activations, 'ringwood_traces': traces, 'ringwood_corrected_diagnostics': ringwood_diagnostics}
    (ROOT/'reports/preference_review_2026_10_08/vec_coverage_activations.json').write_text(json.dumps(payload, indent=2)+'\n')
    print(json.dumps(summary, indent=2))
    print(json.dumps(origin_summary, indent=2))
    print('Protected flow equality checks:', protected_checks)


if __name__ == '__main__':
    main()
