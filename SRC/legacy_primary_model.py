from __future__ import annotations

import pandas as pd

from SRC.constants import PARTIES


LEGACY_PVI_COLUMNS = {
    "ALP": "ALP_pvi",
    "LNP": "LNP_pvi",
    "GRN": "GRN_pvi",
    "IND": "IND_pvi",
    "OTH": "OTH_pvi",
}


def build_legacy_primary_table(
    primary_inputs: pd.DataFrame,
    targets: dict[str, float],
    on_alpha: float = 0.6,
) -> pd.DataFrame:
    """Reproduce the legacy Sheet's lower-house primary calculation.

    ``targets`` are statewide percentages (for example ``24.4`` for ON).
    PVI and ON-strength inputs are decimal proportions, matching the legacy
    workbook. The output party columns are decimal seat shares.
    """

    required = {
        "district",
        "region",
        "seat_type",
        "held_by",
        "ON_strength",
        *LEGACY_PVI_COLUMNS.values(),
    }
    missing = sorted(required.difference(primary_inputs.columns))
    if missing:
        raise ValueError(f"Legacy primary inputs missing columns: {missing}")

    missing_targets = sorted(set(PARTIES).difference(targets))
    if missing_targets:
        raise ValueError(f"Primary targets missing parties: {missing_targets}")

    out = primary_inputs.copy()

    for party, pvi_column in LEGACY_PVI_COLUMNS.items():
        target = float(targets[party]) / 100
        out[f"{party}_pre"] = target + pd.to_numeric(
            out[pvi_column], errors="raise"
        )

    on_strength = pd.to_numeric(out["ON_strength"], errors="raise").clip(
        lower=0
    )
    out["ON_weight"] = on_strength.pow(float(on_alpha))

    mean_weight = out["ON_weight"].mean()
    if mean_weight <= 0:
        out["ON_index_multiplier"] = 0.0
    else:
        out["ON_index_multiplier"] = out["ON_weight"] / mean_weight

    out["ON_share"] = (
        float(targets["ON"]) / 100 * out["ON_index_multiplier"]
    )

    positive_components = pd.DataFrame(index=out.index)
    for party in ["ALP", "LNP", "GRN", "IND", "OTH"]:
        positive_components[party] = out[f"{party}_pre"].clip(lower=0)
    positive_components["ON"] = out["ON_share"].clip(lower=0)

    row_totals = positive_components.sum(axis=1)
    if (row_totals <= 0).any():
        districts = out.loc[row_totals <= 0, "district"].tolist()
        raise ValueError(f"Primary vote total is zero for districts: {districts}")

    for party in PARTIES:
        out[party] = positive_components[party] / row_totals

    return out


def build_corrected_primary_table(
    primary_inputs: pd.DataFrame,
    targets: dict[str, float],
    on_alpha: float = 0.6,
    pvi_strengths: dict[str, float] | None = None,
    iterations: int = 100,
    tolerance: float = 1e-12,
) -> pd.DataFrame:
    """Build legacy-style seat primaries calibrated to statewide targets.

    Unlike the former web port, calibration always begins with the raw PVI
    and SA1-derived ON inputs for the requested scenario. It never reuses a
    ``SEAT HELPER`` snapshot produced under a different statewide ON vote.
    """

    target_total = sum(float(targets[party]) for party in PARTIES)
    if target_total <= 0:
        raise ValueError("Primary targets must have a positive total")

    target_shares = {
        party: max(0.0, float(targets[party])) / target_total
        for party in PARTIES
    }

    adjusted_inputs = primary_inputs.copy()
    for party, strength in (pvi_strengths or {}).items():
        column = LEGACY_PVI_COLUMNS.get(party)
        if column is None:
            raise ValueError(f"Unknown PVI persistence party: {party}")
        strength = float(strength)
        if strength < 0:
            raise ValueError(f"PVI persistence cannot be negative: {party}={strength}")
        adjusted_inputs[column] = pd.to_numeric(
            adjusted_inputs[column], errors="raise"
        ) * strength

    legacy = build_legacy_primary_table(
        primary_inputs=adjusted_inputs,
        targets=targets,
        on_alpha=on_alpha,
    )
    components = legacy[PARTIES].copy()

    # A zero statewide target means the party is absent from the scenario.
    for party in PARTIES:
        if target_shares[party] == 0:
            components[party] = 0.0

    for _ in range(iterations):
        row_totals = components.sum(axis=1)
        if (row_totals <= 0).any():
            raise ValueError("Corrected primary calibration produced a zero row")

        shares = components.div(row_totals, axis=0)
        current = shares.mean(axis=0)

        max_error = max(
            abs(float(current[party]) - target_shares[party])
            for party in PARTIES
        )
        if max_error <= tolerance:
            break

        for party in PARTIES:
            target = target_shares[party]
            observed = float(current[party])
            if target == 0:
                components[party] = 0.0
            elif observed <= 0:
                raise ValueError(
                    f"Cannot calibrate {party}: no positive seat-level mass"
                )
            else:
                components[party] *= target / observed
    else:
        raise ValueError(
            "Corrected primary calibration did not converge within "
            f"{iterations} iterations"
        )

    row_totals = components.sum(axis=1)
    calibrated = components.div(row_totals, axis=0)
    out = legacy.copy()
    for party in PARTIES:
        out[party] = calibrated[party]

    return out


def deplete_on_primary_source_matrix(
    source_matrix: dict,
    on_level: float,
    max_depletion: float = 0.75,
    start_level: float = 10.0,
    full_level: float = 30.0,
) -> dict:
    """Reduce OTH's primary donor role as ON grows.

    Released OTH weight is reassigned two-thirds to LNP and one-third to ALP,
    matching the development configuration tested before production.
    """
    from copy import deepcopy

    if full_level <= start_level:
        raise ValueError("ON primary donor depletion full level must exceed start level")
    progress = max(0.0, min(1.0, (float(on_level) - start_level) / (full_level - start_level)))
    depletion = max(0.0, min(1.0, float(max_depletion))) * progress
    result = deepcopy(source_matrix)
    for row in result.values():
        released = float(row.get("OTH", 0.0) or 0.0) * depletion
        row["OTH"] = float(row.get("OTH", 0.0) or 0.0) - released
        row["LNP"] = float(row.get("LNP", 0.0) or 0.0) + released * 2 / 3
        row["ALP"] = float(row.get("ALP", 0.0) or 0.0) + released / 3
    return result


def _calibrate_primary_components(
    components: pd.DataFrame,
    targets: dict[str, float],
    iterations: int = 300,
    tolerance: float = 1e-12,
) -> pd.DataFrame:
    out = components[PARTIES].clip(lower=1e-12).copy()
    total = sum(float(targets[p]) for p in PARTIES)
    target = {p: float(targets[p]) / total for p in PARTIES}
    for _ in range(iterations):
        shares = out.div(out.sum(axis=1), axis=0)
        current = shares.mean()
        if max(abs(float(current[p]) - target[p]) for p in PARTIES) <= tolerance:
            return shares
        for party in PARTIES:
            out[party] *= target[party] / float(current[party])
    raise ValueError("ON primary donor calibration did not converge")


def apply_seat_primary_adjustments(
    current: pd.DataFrame,
    adjustments: pd.DataFrame,
    targets: dict[str, float],
    retirement_penalty_pp: float = 1.0,
    sophomore_bonus_pp: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply editable seat effects, then restore exact statewide targets.

    Effects are additive percentage points in the nominated party's primary.
    The opposite movement is shared proportionally across the other parties.
    A final calibration preserves the user's statewide polling inputs.
    """
    if adjustments is None or adjustments.empty:
        return current.copy(), pd.DataFrame()

    out = current.copy()
    diagnostics = []
    district_index = {
        str(district).strip(): index
        for index, district in out["district"].items()
    }

    for _, row in adjustments.iterrows():
        if not bool(row.get("enabled", True)):
            continue
        district = str(row.get("district", "")).strip()
        party = str(row.get("party", "")).strip().upper()
        if district not in district_index or party not in PARTIES:
            continue

        retirement_value = row.get("retirement_penalty_pp")
        sophomore_value = row.get("sophomore_bonus_pp")
        retirement = (
            float(retirement_value)
            if pd.notna(retirement_value)
            else float(retirement_penalty_pp)
        ) if bool(row.get("retiring_incumbent", False)) else 0.0
        sophomore = (
            float(sophomore_value)
            if pd.notna(sophomore_value)
            else float(sophomore_bonus_pp)
        ) if bool(row.get("first_re_election", False)) else 0.0
        candidate = float(row.get("candidate_strength_pp") or 0.0) if pd.notna(
            row.get("candidate_strength_pp")
        ) else 0.0
        manual = float(row.get("manual_adjustment_pp") or 0.0) if pd.notna(
            row.get("manual_adjustment_pp")
        ) else 0.0
        requested_pp = -retirement + sophomore + candidate + manual
        if abs(requested_pp) <= 1e-12:
            continue

        index = district_index[district]
        before = float(out.at[index, party])
        requested = requested_pp / 100
        after = min(1.0 - 1e-9, max(1e-9, before + requested))
        actual = after - before
        others = [other for other in PARTIES if other != party]
        other_total = float(out.loc[index, others].sum())
        if other_total <= 0:
            continue
        out.at[index, party] = after
        scale = (other_total - actual) / other_total
        out.loc[index, others] = out.loc[index, others] * scale
        diagnostics.append({
            "district": district,
            "party": party,
            "retirement_pp": -retirement,
            "sophomore_pp": sophomore,
            "candidate_strength_pp": candidate,
            "manual_adjustment_pp": manual,
            "requested_total_pp": requested_pp,
            "pre_calibration_change_pp": actual * 100,
            "notes": row.get("notes", ""),
        })

    if not diagnostics:
        return current.copy(), pd.DataFrame()

    calibrated = _calibrate_primary_components(out[PARTIES], targets)
    for party in PARTIES:
        out[party] = calibrated[party]
    diagnostic_df = pd.DataFrame(diagnostics)
    for index, row in diagnostic_df.iterrows():
        district_mask = out["district"].eq(row["district"])
        original_mask = current["district"].eq(row["district"])
        diagnostic_df.at[index, "final_change_pp"] = (
            float(out.loc[district_mask, row["party"]].iloc[0])
            - float(current.loc[original_mask, row["party"]].iloc[0])
        ) * 100
    return out, diagnostic_df


def apply_on_primary_donor_geography(
    primary_inputs: pd.DataFrame,
    current: pd.DataFrame,
    targets: dict[str, float],
    source_matrix: dict,
    strength: float,
    on_alpha: float = 0.6,
) -> pd.DataFrame:
    """Blend toward explicit, seat-class ON primary donor allocation.

    ``strength=0`` reproduces the corrected proportional model and
    ``strength=1`` applies the explicit source construction in full. Both
    endpoints—and every blend between them—preserve statewide targets.
    """
    strength = max(0.0, min(1.0, float(strength)))
    if strength == 0:
        return current.copy()

    non_on = [p for p in PARTIES if p != "ON"]
    on = current["ON"].reset_index(drop=True)
    seat_types = primary_inputs["seat_type"].reset_index(drop=True)
    requested = pd.DataFrame(index=primary_inputs.index)
    for party in non_on:
        requested[party] = [
            float(on.iloc[i])
            * float(source_matrix.get(seat_types.iloc[i], {}).get(party, 0.0) or 0.0)
            for i in range(len(primary_inputs))
        ]

    pre_targets = {
        party: float(targets[party]) + requested[party].mean() * 100
        for party in non_on
    }
    pre_targets["ON"] = 0.0
    pre = build_corrected_primary_table(
        primary_inputs, pre_targets, on_alpha=on_alpha
    )
    components = pre[PARTIES].copy()

    for i in primary_inputs.index:
        remaining = float(on.iloc[i])
        available = {p: float(components.loc[i, p]) for p in non_on}
        weights = {
            p: float(source_matrix.get(seat_types.iloc[i], {}).get(p, 0.0) or 0.0)
            for p in non_on
        }
        actual = {p: 0.0 for p in non_on}
        active = set(non_on)
        while remaining > 1e-12 and active:
            weight_total = sum(weights[p] for p in active)
            shares = (
                {p: weights[p] / weight_total for p in active}
                if weight_total > 0
                else {p: available[p] / sum(available[q] for q in active) for p in active}
            )
            moved = 0.0
            exhausted = []
            for party in active:
                take = min(remaining * shares[party], available[party])
                actual[party] += take
                available[party] -= take
                moved += take
                if available[party] <= 1e-12:
                    exhausted.append(party)
            remaining -= moved
            active.difference_update(exhausted)
            if moved <= 1e-15:
                break
        for party in non_on:
            components.loc[i, party] -= actual[party]
        components.loc[i, "ON"] = float(on.iloc[i]) - max(0.0, remaining)

    explicit = _calibrate_primary_components(components, targets)
    result = current.copy()
    for party in PARTIES:
        result[party] = (1 - strength) * current[party] + strength * explicit[party]
    return result
