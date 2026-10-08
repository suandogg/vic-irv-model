"""Sensitivity, not a calibration of unobserved ballot-origin preferences."""
import copy
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
from SRC.irv import run_irv_all


def main():
    params = load_params()
    inputs = load_legacy_primary_inputs()
    matrices = load_synth_pref_matrices()
    attached = attach_vec_fields(matrices)
    post = apply_production_federal_on_evidence(load_posterior_scenarios())
    ideology = load_ideology_prior()
    adjustments = load_lower_seat_adjustments()
    records = []
    examples = {'PAKENHAM', 'MORWELL', 'PASCOE VALE', 'ASHWOOD', 'YAN YEAN', 'RINGWOOD'}
    for scenario, targets in SCENARIOS.items():
        primary, settings = build_primaries(inputs, params, targets, adjustments)
        for retention in (0, .5, .75, 1):
            results = {}
            for name in ('reference', 'vec_field_coverage'):
                current = variant(copy.deepcopy(settings), name)
                current['scalar_params']['PARCEL_ORIGIN_RETENTION'] = retention
                result = run_irv_all(primary, matrices if name == 'reference' else attached, current, post, ideology)
                if isinstance(result, tuple):
                    result = result[0]
                import pandas as pd
                results[name] = pd.DataFrame(result).set_index('district')
            ref, trial = results['reference'], results['vec_field_coverage']
            changed = trial.index[trial.winner != ref.winner].tolist()
            demo = []
            for seat, row in trial.iterrows():
                if seat.upper() in examples:
                    demo.append({'seat': seat, 'reference_winner': ref.loc[seat, 'winner'], 'corrected_winner': row.winner,
                                 'ALP_2PP': row.ALP_2PP*100, 'ALP_2PP_delta_pp': (row.ALP_2PP-ref.loc[seat, 'ALP_2PP'])*100})
            records.append({'scenario': scenario, 'retention': retention, 'reference_counts': ref.winner.value_counts().to_dict(),
                            'corrected_counts': trial.winner.value_counts().to_dict(), 'changed_seats_at_same_retention': changed, 'examples': demo})
    (ROOT/'reports/preference_review_2026_10_08/vec_retention_sensitivity.json').write_text(json.dumps(records, indent=2)+'\n')
    for r in records:
        print(r['scenario'], r['retention'], r['corrected_counts'], r['changed_seats_at_same_retention'])


if __name__ == '__main__':
    main()
