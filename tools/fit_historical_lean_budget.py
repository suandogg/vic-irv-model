"""Historical component estimates and a non-active partial nowcast proposal.

One-way random-intercept moments split within/between-region variation.
Cross-validated covariance shrinkage regularises the established-party block.
This estimates one historical transition, not calibrated predictive coverage.
"""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from SRC.constants import PARTIES
from SRC.nowcast_uncertainty import validate_config


def components(values,groups):
    x=np.asarray(values,dtype=float)
    groups=np.asarray(groups)
    labels=sorted(set(groups))
    n,p=x.shape
    g=len(labels)
    if n<=g or g<2 or not np.isfinite(x).all():
        raise ValueError('Insufficient finite grouped observations')
    grand=x.mean(axis=0)
    residual=np.zeros_like(x)
    between=np.zeros((p,p))
    sizes=[]
    for label in labels:
        index=groups==label
        mean=x[index].mean(axis=0)
        residual[index]=x[index]-mean
        sizes.append(index.sum())
        between+=index.sum()*np.outer(mean-grand,mean-grand)
    within=residual.T@residual/(n-g)
    ms_between=between/(g-1)
    effective_n=(n-np.sum(np.square(sizes))/n)/(g-1)
    region_var=np.maximum(0,(np.diag(ms_between)-np.diag(within))/effective_n)
    return dict(within=within,region_variance=region_var,residual=residual,
                group_count=g,group_sizes=sizes,effective_n=effective_n)


def shrink_correlation(covariance,weight):
    sd=np.sqrt(np.diag(covariance))
    if (sd<=0).any():
        raise ValueError('Cannot fit a zero-variance party correlation')
    correlation=covariance/np.outer(sd,sd)
    return (1-weight)*correlation+weight*np.eye(len(sd))


def choose_shrinkage(values,groups):
    """Leave one district out, re-estimating its regional mean without leakage.

    Scores tune covariance regularisation, NOT forecast election accuracy.
    Districts share one electoral transition, so this is not independent
    election-level cross-validation or proof of out-of-sample calibration.
    """
    x=np.asarray(values,dtype=float)
    groups=np.asarray(groups)
    folds=[]
    for index in range(len(x)):
        keep=np.arange(len(x))!=index
        same=groups[keep]==groups[index]
        if not same.any():
            continue
        fitted=components(x[keep],groups[keep])
        error=x[index]-x[keep][same].mean(axis=0)
        folds.append((fitted['within'],error,1+1/int(same.sum())))
    if not folds:
        raise ValueError('No usable held-out districts')
    rows=[]
    for weight in np.linspace(0,1,101):
        scores=[]
        for covariance,error,mean_variance in folds:
            sd=np.sqrt(np.diag(covariance))
            prediction=shrink_correlation(covariance,weight)*np.outer(sd,sd)*mean_variance
            sign,logdet=np.linalg.slogdet(prediction)
            scores.append(float(logdet+error@np.linalg.solve(prediction,error)) if sign>0 else np.inf)
        rows.append(dict(Identity_weight=float(weight),Mean_conditional_Gaussian_score=float(np.mean(scores)),Folds=len(folds)))
    table=pd.DataFrame(rows)
    best=table.loc[table.Mean_conditional_Gaussian_score.idxmin(),'Identity_weight']
    return float(best),table


def main():
    input_path=ROOT/'reports/historical_lean_evidence_2026_10_29/lean_changes.csv'
    detail=pd.read_csv(input_path)
    mapping_path=ROOT/'data/research/historical_primaries_2026_10_29/region_membership.json'
    membership=json.loads(mapping_path.read_text())
    mapping={seat:region for region,seats in membership['regions'].items() for seat in seats}
    if len(mapping)!=88 or any(len(v)!=11 for v in membership['regions'].values()):
        raise ValueError('Historical membership must cover 88 unique districts, 11 per region')
    if set(detail.District)!=set(mapping):
        raise ValueError('Historical region roster does not match source panel')
    detail['Historical_region']=detail.District.map(mapping)
    core=['ALP','LNP','GRN']
    sample=detail[detail.Major_field_context_subset&detail.Party.isin(core)]
    x=sample.pivot(index='District',columns='Party',values='Lean_change_pp')[core]
    groups=np.array([mapping[seat] for seat in x.index])
    estimates=components(x.to_numpy(),groups)
    weight,scores=choose_shrinkage(x.to_numpy(),groups)
    correlation=shrink_correlation(estimates['within'],weight)
    rows=[]
    for j,party in enumerate(core):
        local=np.sqrt(estimates['within'][j,j])
        regional=np.sqrt(estimates['region_variance'][j])
        rows.append(dict(Party=party,Districts=len(x),Regions=estimates['group_count'],
            Historical_local_SD_pp=float(local),Historical_region_SD_pp=float(regional),
            Historical_total_SD_pp=float(np.hypot(local,regional)),
            Interpretation='Historical component proxy, not a calibrated nowcast SD'))
    # No invented current exceptional-seat assignments or candidate effects.
    # Retained ON/IND/OTH values come from the live snapshot, explicitly NOT fitted.
    snapshot=json.loads((ROOT/'reports/nowcast_architecture_live_snapshot_2026_10_28.json').read_text())
    settings_rows=snapshot['sheets']['FORECAST PARAMS']['values'][1:]
    settings={r[1]:float(r[2]) for r in settings_rows}
    config=dict(local_sd_pp={p:settings['SEAT_PRIMARY_SD_PP'] for p in PARTIES},
        region_sd_pp={p:settings['REGION_PRIMARY_SD_PP'] for p in PARTIES},
        class_sd_pp={},transport_log_sd={},contexts={},tail_df=None,
        provenance='2014–2018 historical component proxy for ALP/LNP/GRN; ON/IND/OTH retain explicit snapshot assumptions. Partial proposal, not fitted full-nowcast probabilities.')
    matrix=np.eye(len(PARTIES))
    for j,party in enumerate(core):
        config['local_sd_pp'][party]=rows[j]['Historical_local_SD_pp']
        config['region_sd_pp'][party]=rows[j]['Historical_region_SD_pp']
        for k,other in enumerate(core):
            matrix[PARTIES.index(party),PARTIES.index(other)]=correlation[j,k]
    config['correlation']=matrix.tolist()
    config=validate_config(config,[]) # No current-seat context inferred from history.
    out=ROOT/'reports/historical_lean_budget_2026_10_29'
    out.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out/'component_estimates.csv',index=False)
    pd.DataFrame(correlation,index=core,columns=core).to_csv(out/'shrunk_within_party_correlation.csv')
    scores.to_csv(out/'covariance_regularisation_scores.csv',index=False)
    detail.to_csv(out/'historical_context_and_region.csv',index=False)
    proposal=dict(status='NOT_ACTIVE; partial historical proxy only',config=config,
        identity_shrinkage_weight=weight,conditional_score_is_forecast_validation=False,
        unresolved=['Only one four-year electoral transition; not calibrated current-error coverage',
            'ON absent from panel; all ON geography/source transport uncertainty still requires explicit assumptions',
            'IND/OTH candidate-field/composition uncertainty not inferred from category residuals',
            'Regional correlation borrows within-region party correlation; only eight historical regions',
            'Current region/subregion transferability is an assumption, not a boundary crosswalk',
            'No fitted subregion variance: do not relabel the historical regional component as an estimated blend',
            'Existing preference SDs and ON-alpha/donor terms remain provisional; new transport scales not set'],
        source_sha256=hashlib.sha256(input_path.read_bytes()+mapping_path.read_bytes()).hexdigest())
    (out/'partial_config_proposal.json').write_text(json.dumps(proposal,indent=2))
    print(pd.DataFrame(rows).to_string(index=False))
    print('Correlation identity shrinkage:',weight)
    print(pd.DataFrame(correlation,index=core,columns=core).to_string())
    print('Historical region sample sizes:',dict(zip(sorted(set(groups)),estimates['group_sizes'])))


if __name__=='__main__':
    main()
