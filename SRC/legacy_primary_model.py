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

    legacy = build_legacy_primary_table(
        primary_inputs=primary_inputs,
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
