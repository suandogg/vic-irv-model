"""Fixed-primary ablations; trial controls are not production recommendations."""
from pathlib import Path
import sys
import copy
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.compare_latent_ranking_shadow import build_primaries
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.params_loader import load_params
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.posterior_loader import load_posterior_scenarios
from SRC.federal_on_evidence_loader import apply_production_federal_on_evidence
from SRC.ideology_loader import load_ideology_prior
from SRC.seat_adjustments_loader import load_lower_seat_adjustments
from SRC.irv import run_irv_all
from tools.trial_posterior_reliability import seat_count_trial
from tools.trial_oth_matrix_rebuild import rebuild_oth_matrices

SCENARIOS = {
    "2022": dict(ALP=36.66,LNP=34.48,GRN=11.5,ON=.28,IND=5.55,OTH=11.53),
    "ON18": dict(ALP=29,LNP=32,GRN=12,ON=18,IND=4.5,OTH=4.5),
    "ON20": dict(ALP=25,LNP=30,GRN=14,ON=20,IND=5.5,OTH=5.5),
    "ON24": dict(ALP=25,LNP=28,GRN=12,ON=24,IND=5.5,OTH=5.5),
}

def variant(params, name):
    p = copy.deepcopy(params)
    s = p["scalar_params"]
    if name == "no_incomplete_matrix_anchor":
        s["TRIAL_NO_INCOMPLETE_MATRIX_ANCHOR"] = True
    if name in ("single_on_baseline", "matrix_source_only"):
        s["TRIAL_SINGLE_ON_BASELINE"] = True
        s["TRIAL_MATRIX_KEEP_TRANSFORMS"] = name == "matrix_source_only"
    if name == "on_no_extra_transforms":
        s["TRIAL_ON_NO_EXTRA_TRANSFORMS"] = True
    if name in ("no_siphon", "simplified"):
        s["SIPHON_STRENGTH_ON"] = 0
    if name in ("no_geography", "simplified"):
        p["geography_adjustments"] = {}
    if name == "no_on_recipient_geography":
        for adjustment in p["geography_adjustments"].values():
            adjustment["ON"] = 0
    if name == "no_non_on_recipient_geography":
        s["NON_ON_GEOGRAPHY_STRENGTH"] = 0
    if name in ("no_constraints", "simplified"):
        s.update(MAJOR_PAIR_MAX=1,THREE_WAY_MAX=1,IND_OTH_MAX=1)
        # Check the engine's actual floor key rather than assuming its name.
        s["TRIAL_NO_FLOOR"] = True
    if name in ("no_synthetic_priority", "simplified"):
        s["TRIAL_NO_SYNTHETIC_ON_PRIORITY"] = True
    return p

def main():
    params=load_params(); inputs=load_legacy_primary_inputs()
    matrices=load_synth_pref_matrices(); ideology=load_ideology_prior()
    posterior=apply_production_federal_on_evidence(load_posterior_scenarios())
    adjustments=load_lower_seat_adjustments(); rows=[]; summaries=[]
    out=ROOT/"reports"/"preference_review_2026_10_08"; out.mkdir(exist_ok=True)
    manifest=[]
    for path in sorted((ROOT/"data"/"raw").glob("*.csv")):
        manifest.append(dict(File=path.name,SHA256=hashlib.sha256(path.read_bytes()).hexdigest()))
    pd.DataFrame(manifest).to_csv(out/"input_manifest.csv",index=False)
    for scenario, targets in SCENARIOS.items():
        primary, p=build_primaries(inputs,params,targets,adjustments)
        primary.to_csv(out/f"primaries_{scenario}.csv",index=False)
        reference=None
        for name in ("reference","no_incomplete_matrix_anchor","oth_params_rebuild","matrix_source_only","single_on_baseline","on_no_extra_transforms","no_on_recipient_geography","no_non_on_recipient_geography","no_siphon","no_geography","no_constraints","no_synthetic_priority","simplified","seat_reliability_5","seat_reliability_10","seat_reliability_20"):
            post=seat_count_trial(posterior,int(name.rsplit("_",1)[1])) if name.startswith("seat_reliability_") else posterior
            trial_matrices = rebuild_oth_matrices(matrices, p) if name == "oth_params_rebuild" else matrices
            result=run_irv_all(primary,trial_matrices,variant(p,name),post,ideology)
            if isinstance(result,tuple): result=result[0]
            result=pd.DataFrame(result)
            if reference is None: reference=result.copy()
            merged=result.merge(reference,on="district",suffixes=("","_reference"))
            changed=merged["winner"]!=merged["winner_reference"]
            counts=result["winner"].value_counts().to_dict()
            summaries.append(dict(Scenario=scenario,Variant=name,ChangedWinners=int(changed.sum()),ONFinalTwo=int(((result["winner"]=="ON")|(result["runner_up"]=="ON")).sum()),**counts))
            merged["Scenario"]=scenario; merged["Variant"]=name
            rows.append(merged)
    pd.DataFrame(summaries).fillna(0).to_csv(out/"summary.csv",index=False)
    pd.concat(rows).to_csv(out/"seat_results.csv",index=False)
    print(pd.DataFrame(summaries).fillna(0).to_string(index=False))

if __name__ == "__main__": main()
