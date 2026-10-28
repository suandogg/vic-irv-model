"""Opt-in nowcast building blocks; no fitted scales or automatic candidates.

District-lean errors replace the old regional/local primary residuals. Source
transport uncertainty is separate from existing source-flow perturbations.
Configuration is explicit: no numerical research assumptions are activated here.
"""
import copy
import numpy as np
from SRC.constants import PARTIES
from SRC.forecast_patterns import balance_primary_pattern

SOURCES = ('vec','federal','special','generic')


def validate_config(config, districts):
    allowed = {'local_sd_pp','region_sd_pp','class_sd_pp','correlation',
               'tail_df','contexts','transport_log_sd','provenance'}
    if not isinstance(config,dict) or set(config)-allowed:
        raise ValueError('Unknown structured nowcast configuration')
    out = copy.deepcopy(config)
    for field in ('local_sd_pp','region_sd_pp','class_sd_pp'):
        values = out.get(field,{})
        if not isinstance(values,dict) or set(values)-set(PARTIES):
            raise ValueError(field+' must use party codes')
        out[field] = {p:float(values.get(p,0)) for p in PARTIES}
        if any(not np.isfinite(x) or not 0<=x<=30 for x in out[field].values()):
            raise ValueError(field+' must be finite, nonnegative, at most 30 pp')
    correlation = np.asarray(out.get('correlation',np.eye(len(PARTIES))),dtype=float)
    if (correlation.shape!=(len(PARTIES),len(PARTIES)) or not np.isfinite(correlation).all()
            or not np.allclose(correlation,correlation.T,atol=1e-12,rtol=0)
            or not np.allclose(np.diag(correlation),1,atol=1e-12,rtol=0)
            or np.linalg.eigvalsh(correlation).min() < -1e-10):
        raise ValueError('Party correlation must be symmetric positive semidefinite with unit diagonal')
    out['correlation'] = correlation.tolist()
    df = out.get('tail_df')
    if df is not None and (not np.isfinite(df) or df<=2):
        raise ValueError('Tail degrees of freedom must exceed two')
    contexts = out.get('contexts',{})
    if not isinstance(contexts,dict) or set(contexts)-set(districts):
        raise ValueError('Context district not found in forecast field')
    for seat, context in contexts.items():
        if not isinstance(context,dict) or set(context)-{'local_multiplier','candidate_sd_pp','note'}:
            raise ValueError('Unknown candidate/context field')
        for field,default,maximum in [('local_multiplier',1,10),('candidate_sd_pp',0,30)]:
            values = context.get(field,{})
            if not isinstance(values,dict) or set(values)-set(PARTIES):
                raise ValueError('Context effects must use party codes')
            context[field] = {p:float(values.get(p,default)) for p in PARTIES}
            if any(not np.isfinite(x) or not 0<=x<=maximum for x in context[field].values()):
                raise ValueError('Invalid context scale')
        if any(context['candidate_sd_pp'].values()) and not str(context.get('note','')).strip():
            raise ValueError('Candidate uncertainty needs an explanatory context note')
    out['contexts'] = contexts
    transport = out.get('transport_log_sd',{})
    if not isinstance(transport,dict) or set(transport)-set(SOURCES):
        raise ValueError('Unknown preference transport source')
    out['transport_log_sd'] = {s:float(transport.get(s,0)) for s in SOURCES}
    if any(not np.isfinite(x) or not 0<=x<=2 for x in out['transport_log_sd'].values()):
        raise ValueError('Invalid preference transport SD')
    if not isinstance(out.get('provenance'),str) or not out['provenance'].strip():
        raise ValueError('Structured nowcast requires uncertainty-assumption provenance')
    return out


def draw_vectors(rng,count,correlation,df=None):
    """Party covariance; common t scale preserves joint substitution directions."""
    eigenvalues,eigenvectors = np.linalg.eigh(correlation)
    root = eigenvectors @ np.diag(np.sqrt(np.maximum(eigenvalues,0)))
    result = rng.normal(size=(count,len(PARTIES))) @ root.T
    if df is not None:
        result *= np.sqrt((df-2)/rng.chisquare(df,size=count))[:,None]
    return result


def perturb_district_leans(adjusted,config,rng,subregions=None,subregion_fraction=0):
    """Joint primary-pp lean errors; preserve actual production statewide totals.

    Scales/correlation describe errors BEFORE nonnegativity and balancing.
    Context candidate terms describe strength uncertainty for an existing field,
    NOT a candidate-appearance model. Exact zero cells remain zero.
    """
    config = validate_config(config,list(adjusted.district))
    if not 0<=subregion_fraction<=1:
        raise ValueError('Invalid subregion variance fraction')
    if subregion_fraction and (subregions is None or set(subregions)!=set(adjusted.district)):
        raise ValueError('Structured geography needs all district subregions')
    base = adjusted[PARTIES].to_numpy(dtype=float)
    if (base<0).any() or not np.isfinite(base).all():
        raise ValueError('Invalid primary table')
    active = any(any(config[k].values()) for k in ('local_sd_pp','region_sd_pp','class_sd_pp'))
    active |= any(any(c['candidate_sd_pp'].values()) for c in config['contexts'].values())
    if not active:
        return adjusted.copy(),np.zeros_like(base)
    corr = np.asarray(config['correlation'])
    df = config.get('tail_df')
    def grouped(labels):
        keys = sorted(set(labels))
        vectors = dict(zip(keys,draw_vectors(rng,len(keys),corr,df)))
        return np.array([vectors[k] for k in labels])
    regional = grouped(list(adjusted.region))
    if subregion_fraction:
        lower = grouped([subregions[d] for d in adjusted.district])
        regional = np.sqrt(1-subregion_fraction)*regional+np.sqrt(subregion_fraction)*lower
    local = draw_vectors(rng,len(base),corr,df)
    for index,seat in enumerate(adjusted.district):
        context = config['contexts'].get(seat)
        if context:
            local[index] *= [context['local_multiplier'][p] for p in PARTIES]
    scales = lambda field:np.array([config[field][p] for p in PARTIES])/100
    error = (local*scales('local_sd_pp')+regional*scales('region_sd_pp')
             +grouped(list(adjusted.seat_type))*scales('class_sd_pp'))
    for index,seat in enumerate(adjusted.district):
        context = config['contexts'].get(seat)
        if context and any(context['candidate_sd_pp'].values()):
            error[index] += rng.normal(size=len(PARTIES))*np.array(
                [context['candidate_sd_pp'][p] for p in PARTIES])/100
    values = np.where(base>0,np.maximum(base+error,1e-12),0)
    log_tilt = np.zeros_like(base)
    np.log(np.divide(values,base,out=np.ones_like(base),where=base>0),out=log_tilt)
    result = adjusted.copy()
    result[PARTIES] = balance_primary_pattern(base,log_tilt)
    return result,error


def draw_transport(config,rng):
    """One source/origin/recipient discrepancy per election, shared across seats.

    This represents possible systematic misapplication of a source. It is not
    sample-size error and does not assign probabilities to alternative models.
    """
    return {source:{origin:dict(zip(PARTIES,rng.normal(size=len(PARTIES))*sd))
                    for origin in PARTIES}
            for source,sd in config['transport_log_sd'].items() if sd>0}
