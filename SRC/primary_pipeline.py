"""Shared, unchanged October primary construction for calculator and forecasts."""
from SRC.legacy_primary_model import (
    apply_seat_primary_adjustments, apply_on_primary_donor_geography,
    build_corrected_primary_table, deplete_on_primary_source_matrix,
)
from SRC.lnp_precollapse_loader import apply_lnp_precollapse


def params_for_scenario(params, targets):
    result = dict(params)
    result['scalar_params'] = dict(params.get('scalar_params', {}))
    total = sum(max(0.0, float(v)) for v in targets.values())
    result['scalar_params']['SCENARIO_ON_PRIMARY'] = (
        max(0.0, float(targets.get('ON', 0))) / total * 100 if total else 0.0)
    return result


def build_projected_primaries(primary_inputs, params, targets, seat_adjustments=None):
    scenario_params = params_for_scenario(params, targets)
    scalars = scenario_params['scalar_params']
    on_alpha = float(scalars.get('ON alpha', 0.6) or 0.6)
    grn_pvi_persistence = float(scalars.get('GRN_PVI_PERSISTENCE', 1.0) or 1.0)
    adjusted = build_corrected_primary_table(
        primary_inputs=primary_inputs, targets=targets, on_alpha=on_alpha,
        pvi_strengths={'GRN': grn_pvi_persistence})
    source_matrix = scenario_params.get('on_vote_source_matrix', {})
    depletion_strength = float(scalars.get('ON_PRIMARY_OTH_DEPLETION_STRENGTH', 0.0) or 0.0)
    if depletion_strength > 0:
        source_matrix = deplete_on_primary_source_matrix(
            source_matrix, on_level=scalars['SCENARIO_ON_PRIMARY'],
            max_depletion=depletion_strength,
            start_level=float(scalars.get('ON_PRIMARY_OTH_DEPLETION_START', 10.0)),
            full_level=float(scalars.get('ON_PRIMARY_OTH_DEPLETION_FULL', 30.0)))
    adjusted = apply_on_primary_donor_geography(
        primary_inputs=primary_inputs, current=adjusted, targets=targets,
        source_matrix=source_matrix,
        strength=float(scalars.get('ON_PRIMARY_DONOR_STRENGTH', 0.0) or 0.0),
        on_alpha=on_alpha)
    adjusted, diagnostics = apply_seat_primary_adjustments(
        current=adjusted, adjustments=seat_adjustments, targets=targets,
        retirement_penalty_pp=float(scalars.get('RETIRING_INCUMBENT_PENALTY_PP', 1.0)),
        sophomore_bonus_pp=float(scalars.get('SOPHOMORE_SURGE_BONUS_PP', 1.0)))
    return apply_lnp_precollapse(adjusted), diagnostics
