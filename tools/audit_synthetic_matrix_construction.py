"""Compare frozen synthetic rows with the documented five-to-six formula.

A numerical match identifies consistency, not historical provenance proof.
Zero raw rows are kept missing, never fabricated into historical evidence.
"""
from pathlib import Path
import sys
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from SRC.loaders import clean_percent
from SRC.matrix_loader import clean_district_name, load_synth_pref_matrices
from SRC.params_loader import load_params

def main():
    raw=pd.read_csv(ROOT/"data/raw/SYNTH PREF MATRIX.csv",header=None)
    params=load_params(); matrices=load_synth_pref_matrices(); rows=[]
    classes={str(k).strip().lower():k for k in params["on_row_prior"]}
    seen=set()
    for start in range(0,len(raw)-8,10):
        seat=clean_district_name(raw.iloc[start,0])
        if seat not in matrices or seat in seen: continue
        seen.add(seat)
        cls=classes.get(str(raw.iloc[start+1,0]).strip().lower())
        if cls is None: raise ValueError(f"Unmapped matrix class {seat}")
        original={str(raw.iloc[r,0]).strip().upper():{p:float(clean_percent(raw.iloc[r,i+1]) or 0) for i,p in enumerate(["ALP","LNP","GRN","IND","OTH"])} for r in range(start+3,start+8)}
        for origin,current in matrices[seat]["matrix"].items():
            if origin=="ON":
                expected={p:float(params["on_row_prior"][cls].get(p,0) or 0) for p in current}
                raw_total=None; basis="ON row prior"
            else:
                historical=original[origin]; raw_total=sum(historical.values())
                prior=float(params["on_column_prior"][origin][cls] or 0)
                expected={p:(prior if p=="ON" else historical.get(p,0)*(1-prior)) if raw_total>0 else 0 for p in current}
                basis="Historical destinations scaled by 1-ON prior" if raw_total>0 else "Empty historical row retained"
            errors={p:float(current.get(p,0) or 0)-expected[p] for p in expected}
            inferred_errors=[float(current.get(p,0) or 0)-v*(1-float(current.get("ON",0) or 0)) for p,v in original.get(origin,{}).items()] if raw_total else []
            rows.append(dict(Seat=seat,SeatType=cls,Origin=origin,RawRowTotal=raw_total,Construction=basis,MaxAbsoluteDifferencePP=100*max(abs(e) for e in errors.values()),MatchesWithin001PP=max(abs(e) for e in errors.values())<=.0001,MatchesUsingStoredONShare=max((abs(e) for e in inferred_errors),default=0)<=.0001 if raw_total else None,HistoricalZeroDestinations=[p for p,v in original.get(origin,{}).items() if p!=origin and v==0],Synthetic=current,Expected=expected))
    summary=dict(Seats=len(matrices),Rows=len(rows),MatchesWithin001PP=sum(r["MatchesWithin001PP"] for r in rows),NonemptyHistoricalRows=sum(r["RawRowTotal"] is not None and r["RawRowTotal"]>0 for r in rows),EmptyHistoricalRows=sum(r["RawRowTotal"]==0 for r in rows),ONRows=sum(r["Origin"]=="ON" for r in rows),MismatchSeats=sorted({r["Seat"] for r in rows if not r["MatchesWithin001PP"]}))
    out=ROOT/"reports/preference_review_2026_10_08/synthetic_construction_audit.json"
    summary["MatchesUsingStoredONShare"]=sum(r["MatchesUsingStoredONShare"] is True for r in rows)
    out.write_text(json.dumps(dict(Summary=summary,Rows=rows),indent=2)+"\n")
    print(json.dumps(summary,indent=2))

if __name__=="__main__": main()
