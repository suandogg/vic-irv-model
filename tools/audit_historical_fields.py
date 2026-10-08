"""Compare legacy matrix support with explicit extracted category-exit fields.

This is a diagnostic join, not an assertion of identical row provenance.
"""
from pathlib import Path
import sys
import json
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from SRC.loaders import clean_percent
from SRC.matrix_loader import clean_district_name, load_synth_pref_matrices

SOURCE = ROOT.parent / "vic_irv_model_restore_work/data/development"


def main():
    flows = pd.read_csv(SOURCE / "VEC_2022_CATEGORY_FLOWS_LONG.csv")
    candidates = pd.read_csv(SOURCE / "VEC_2022_CANDIDATE_CLASSIFICATION.csv")
    trial_candidates = pd.read_csv(ROOT / "data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv")
    keys = ["Electorate", "CandidateName"]
    classification = candidates[keys+["BroadCategory"]].merge(trial_candidates[keys+["BroadCategory"]], on=keys, how="outer", suffixes=("_extraction", "_trial"), indicator=True)
    mismatches = classification[(classification["_merge"] != "both") | (classification.BroadCategory_extraction != classification.BroadCategory_trial)]
    fields = {}
    for (seat, origin), group in flows.groupby(["Electorate", "EliminatedCategory"]):
        if group.AliveSetAfter.nunique() != 1:
            raise ValueError(f"Conflicting extracted fields: {seat}/{origin}")
        fields[(seat.upper(), origin)] = (set(group.AliveSetAfter.iloc[0].split("+")), dict(zip(group.RecipientCategory, group.Share)))
    raw = pd.read_csv(ROOT / "data/raw/SYNTH PREF MATRIX.csv", header=None)
    matrices = load_synth_pref_matrices()
    rows, cells, seen = [], [], set()
    for start in range(0, len(raw)-8, 10):
        seat = clean_district_name(raw.iloc[start, 0])
        if seat not in matrices or seat in seen:
            continue
        seen.add(seat)
        for r in range(start+3, start+8):
            origin = str(raw.iloc[r, 0]).strip().upper()
            historical = {p: float(clean_percent(raw.iloc[r, i+1]) or 0) for i,p in enumerate(["ALP", "LNP", "GRN", "IND", "OTH"])}
            evidence = fields.get((seat, origin))
            alive, shares = evidence if evidence else (set(), {})
            positive_outside = [p for p,v in historical.items() if v > 0 and p not in alive] if evidence else []
            missing_inside = [p for p in alive if historical.get(p, 0) == 0]
            rows.append(dict(Seat=seat, Origin=origin, LegacyRowNonempty=sum(historical.values()) > 0, ExtractedFieldAvailable=bool(evidence), ExtractedAliveSet="+".join(sorted(alive)), LegacyPositiveOutsideExtractedField="+".join(positive_outside), LegacyZerosInsideExtractedField="+".join(sorted(missing_inside))))
            for p,v in historical.items():
                if p == origin:
                    continue
                status = "no extracted category-exit field" if not evidence else "outside extracted field" if p not in alive else "inside extracted field"
                cells.append(dict(Seat=seat, Origin=origin, Destination=p, LegacyShare=v, LegacyZero=v == 0, ExtractedFieldStatus=status, ExtractedShare=shares.get(p, 0) if p in alive else None))
    out = ROOT / "reports/preference_review_2026_10_08"
    frame, cellframe = pd.DataFrame(rows), pd.DataFrame(cells)
    frame.to_csv(out / "historical_field_row_audit.csv", index=False)
    cellframe.to_csv(out / "historical_field_cell_audit.csv", index=False)
    mismatches.to_csv(out / "historical_field_classification_mismatches.csv", index=False)
    summary = dict(ExtractedSeats=int(flows.Electorate.nunique()), ExtractedCategoryExitFields=len(fields), LegacyRows=len(rows), LegacyNonemptyRows=int(frame.LegacyRowNonempty.sum()), RowsWithExtractedField=int(frame.ExtractedFieldAvailable.sum()), ClassificationMismatches=len(mismatches), NonemptyRowsWithPositiveOutsideExtractedField=int((frame.LegacyRowNonempty & frame.LegacyPositiveOutsideExtractedField.ne("")).sum()), ZeroCellsByExtractedFieldStatus=cellframe[cellframe.LegacyZero].ExtractedFieldStatus.value_counts().to_dict(), SourceSHA256=hashlib.sha256((SOURCE / "VEC_2022_CATEGORY_FLOWS_LONG.csv").read_bytes()).hexdigest())
    (out / "historical_field_audit_summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary, indent=2))
    print(frame[frame.Seat.isin(["PAKENHAM", "MORWELL", "PASCOE VALE", "ASHWOOD", "YAN YEAN"])].to_string(index=False))


if __name__ == "__main__":
    main()
