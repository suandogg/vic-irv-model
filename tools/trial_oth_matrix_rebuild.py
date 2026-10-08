"""Isolated OTH construction trial; never edits source matrices or special priors."""
import copy
from SRC.loaders import read_csv_raw, clean_percent
from SRC.matrix_loader import clean_district_name


def rebuild_oth_matrices(matrices, params):
    result = copy.deepcopy(matrices)
    raw = read_csv_raw("SYNTH PREF MATRIX.csv", header=None)
    classes = {str(k).strip().lower(): k for k in params["on_column_prior"]["OTH"]}
    seen = set()
    for start in range(0, len(raw)-8, 10):
        seat = clean_district_name(raw.iloc[start, 0])
        if seat not in result or seat in seen:
            continue
        seen.add(seat)
        cls = classes[str(raw.iloc[start+1, 0]).strip().lower()]
        r = start+7
        if str(raw.iloc[r, 0]).strip().upper() != "OTH":
            raise ValueError(f"Unexpected historical OTH row: {seat}")
        historical = {p: float(clean_percent(raw.iloc[r, i+1]) or 0) for i, p in enumerate(["ALP", "LNP", "GRN", "IND", "OTH"])}
        if sum(historical.values()) == 0:
            continue
        prior = float(params["on_column_prior"]["OTH"][cls])
        if not 0 <= prior <= 1:
            raise ValueError(f"Invalid OTH ON prior: {cls}")
        if abs(float(matrices[seat]["matrix"]["OTH"].get("ON", 0) or 0)-prior) < 1e-12:
            continue  # Avoid unrelated rounding changes in already-matching rows.
        result[seat]["matrix"]["OTH"] = {p: prior if p == "ON" else historical.get(p, 0)*(1-prior) for p in ["ALP", "LNP", "GRN", "ON", "IND", "OTH"]}
    return result
