"""Construct synthetic OTH rows from historical proportions and live PARAMS."""
import copy
import math

from SRC.loaders import read_csv_raw, clean_percent
from SRC.matrix_loader import clean_district_name


def rebuild_oth_matrices(matrices, params, raw=None):
    """Return a copy; preserve empty historical rows and all other sources."""
    result = copy.deepcopy(matrices)
    if raw is None:
        raw = read_csv_raw("SYNTH PREF MATRIX.csv", header=None)
    priors = {str(k).strip().casefold(): float(v)
              for k, v in params["on_column_prior"]["OTH"].items()}
    seen = set()
    for start in range(0, len(raw) - 8, 10):
        seat = clean_district_name(raw.iloc[start, 0])
        if seat not in result or seat in seen:
            continue
        seen.add(seat)
        row = start + 7
        if str(raw.iloc[row, 0]).strip().upper() != "OTH":
            raise ValueError(f"Unexpected historical OTH row: {seat}")
        historical = {p: float(clean_percent(raw.iloc[row, i + 1]) or 0)
                      for i, p in enumerate(["ALP", "LNP", "GRN", "IND", "OTH"])}
        total = sum(historical.values())
        if not total:
            continue  # No evidence to reconstruct (including Narracan).
        if any(not math.isfinite(v) or v < 0 for v in historical.values()):
            raise ValueError(f"Invalid historical OTH shares: {seat}")
        cls = str(raw.iloc[start + 1, 0]).strip().casefold()
        prior = priors[cls]
        if not math.isfinite(prior) or not 0 <= prior <= 1:
            raise ValueError(f"Invalid OTH ON prior: {cls}")
        if abs(float(result[seat]["matrix"]["OTH"].get("ON", 0) or 0) - prior) < 1e-12:
            continue  # Preserve already-matching rows without rounding drift.
        result[seat]["matrix"]["OTH"] = {
            p: prior if p == "ON" else historical.get(p, 0) / total * (1 - prior)
            for p in ["ALP", "LNP", "GRN", "ON", "IND", "OTH"]}
    return result
