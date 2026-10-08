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
from SRC.irv import trace_irv_for_district, trace_preference_diagnostics_for_district
from SRC.constants import PARTIES


def main():
    params = load_params()
    inputs = load_legacy_primary_inputs()
    matrices = load_synth_pref_matrices()
    attached = attach_vec_fields(matrices)
    post = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    adjustments = load_lower_seat_adjustments()
    activations, traces, ringwood_diagnostics = [], {}, {}
    for scenario, targets in SCENARIOS.items():
        primary, settings = build_primaries(inputs, params, targets, adjustments)
        for district, group in primary.groupby('district'):
            seat = str(district).upper()
            item = attached[seat]
            values = group.set_index('party').primary_vote.to_dict()
            votes = {p: float(values.get(p, 0)) for p in PARTIES}
            corrected = variant(settings, 'vec_field_coverage')
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
    payload = {'scope': 'Actual contest holder-round activations only; excludes forced 2PP runs and separate parcel-origin diagnostic calls.', 'summary': summary, 'activations': activations, 'ringwood_traces': traces, 'ringwood_corrected_diagnostics': ringwood_diagnostics}
    (ROOT/'reports/preference_review_2026_10_08/vec_coverage_activations.json').write_text(json.dumps(payload, indent=2)+'\n')
    print(json.dumps(summary, indent=2))
    print(json.dumps(traces['ON18'], indent=2))


if __name__ == '__main__':
    main()
