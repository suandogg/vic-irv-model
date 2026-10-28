from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass

from SRC.constants import PARTIES
from SRC.loaders import read_csv_raw


def _as_bool(value) -> bool:
    return str(value).strip().upper() in {"TRUE", "1", "YES", "Y"}


def _optional_float(value):
    if pd.isna(value) or str(value).strip() == "":
        return None
    return _fraction(value)


def _fraction(value) -> float:
    text = str(value).strip()
    if text.endswith("%"):
        return float(text[:-1]) / 100.0
    return float(value)


def load_lnp_precollapse_inputs(filename="LOWER_LNP_PRECOLLAPSE.csv") -> pd.DataFrame:
    try:
        frame = read_csv_raw(filename).copy()
    except FileNotFoundError:
        return pd.DataFrame()
    required = {
        "Electorate", "OriginCategory", "DestinationCategory", "Share",
        "Enabled", "Strength", "ManualOverrideShare",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"LNP pre-collapse input is missing columns: {sorted(missing)}")
    frame["ElectorateKey"] = frame["Electorate"].astype(str).str.strip().str.upper()
    frame["DestinationCategory"] = frame["DestinationCategory"].astype(str).str.strip().str.upper()
    frame["Share"] = frame["Share"].map(_fraction)
    frame["Strength"] = frame["Strength"].map(_fraction).clip(0, 1)
    frame["Enabled"] = frame["Enabled"].map(_as_bool)
    frame["ManualOverrideShare"] = frame["ManualOverrideShare"].map(_optional_float)
    return frame


@dataclass(frozen=True)
class PrecollapsePlan:
    districts: tuple
    operations: tuple


def compile_lnp_precollapse(districts, inputs):
    """Validate static rules once; preserve input row and destination semantics."""
    districts = tuple(districts)
    keys = [str(d).strip().upper() for d in districts]
    operations = []
    if not inputs.empty:
        for seat_key, rows in inputs[inputs['Enabled']].groupby('ElectorateKey'):
            positions = [i for i,key in enumerate(keys) if key == seat_key]
            if not positions:
                continue
            if len(positions) != 1:
                raise ValueError(f'Expected one primary row for {seat_key}; found {len(positions)}')
            strengths = rows['Strength'].unique()
            if len(strengths) != 1:
                raise ValueError(f'Inconsistent LNP pre-collapse strengths for {seat_key}')
            strength = float(strengths[0])
            shares = {}
            for row in rows.itertuples():
                share = row.ManualOverrideShare if pd.notna(row.ManualOverrideShare) else row.Share
                shares[row.DestinationCategory] = float(share)
            if abs(sum(shares.values()) - 1.0) > 1e-6:
                raise ValueError(f'LNP pre-collapse shares for {seat_key} do not sum to one')
            effective = [strength * shares.get(p,0.0) for p in PARTIES]
            effective[PARTIES.index('LNP')] += 1.0 - strength
            operations.append((positions[0],seat_key,tuple(effective)))
    return PrecollapsePlan(districts,tuple(operations))


def apply_compiled_precollapse(adjusted, plan):
    if tuple(adjusted['district']) != plan.districts:
        raise ValueError('LNP pre-collapse plan district order does not match primary table')
    output = adjusted.copy()
    values = adjusted[PARTIES].to_numpy(copy=True)
    lnp = PARTIES.index('LNP')
    for position,seat_key,effective in plan.operations:
        before = np.nansum(values[position])
        original_lnp = float(values[position,lnp])
        values[position,lnp] = 0.0
        for j,share in enumerate(effective):
            values[position,j] = float(values[position,j]) + original_lnp * share
        if abs(before - np.nansum(values[position])) > 1e-9:
            raise ValueError(f'LNP pre-collapse failed vote conservation in {seat_key}')
    output[PARTIES] = values
    return output


def apply_lnp_precollapse(adjusted: pd.DataFrame, inputs: pd.DataFrame | None = None) -> pd.DataFrame:
    if isinstance(inputs, PrecollapsePlan):
        return apply_compiled_precollapse(adjusted,inputs)
    if inputs is None:
        inputs = load_lnp_precollapse_inputs()
    if inputs.empty:
        return adjusted.copy()
    output = adjusted.copy()
    output["_district_key"] = output["district"].astype(str).str.strip().str.upper()
    for seat_key, rows in inputs[inputs["Enabled"]].groupby("ElectorateKey"):
        mask = output["_district_key"].eq(seat_key)
        if not mask.any():
            continue
        if mask.sum() != 1:
            raise ValueError(f"Expected one primary row for {seat_key}; found {int(mask.sum())}")
        original_lnp = float(output.loc[mask, "LNP"].iloc[0])
        strengths = rows["Strength"].unique()
        if len(strengths) != 1:
            raise ValueError(f"Inconsistent LNP pre-collapse strengths for {seat_key}")
        strength = float(strengths[0])
        shares = {}
        for row in rows.itertuples():
            share = row.ManualOverrideShare if pd.notna(row.ManualOverrideShare) else row.Share
            shares[row.DestinationCategory] = float(share)
        if abs(sum(shares.values()) - 1.0) > 1e-6:
            raise ValueError(f"LNP pre-collapse shares for {seat_key} do not sum to one")
        effective = {party: strength * shares.get(party, 0.0) for party in PARTIES}
        effective["LNP"] += 1.0 - strength
        output.loc[mask, "LNP"] = 0.0
        for destination, share in effective.items():
            output.loc[mask, destination] = (
                output.loc[mask, destination].astype(float) + original_lnp * share
            )
        before = float(adjusted.loc[mask, PARTIES].sum(axis=1).iloc[0])
        after = float(output.loc[mask, PARTIES].sum(axis=1).iloc[0])
        if abs(before - after) > 1e-9:
            raise ValueError(f"LNP pre-collapse failed vote conservation in {seat_key}")
    return output.drop(columns="_district_key")
