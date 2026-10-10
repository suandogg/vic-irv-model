"""Provisional lower-house scenario simulation around the existing calculator.

No polling data are fetched or fitted here. SDs are explicitly editable assumptions.
Regional/local noise preserves each draw's underlying statewide primary totals.
Preference noise is shared across seats and fields, rather than 88 independent
random transfers. Government outputs describe arithmetic, not support agreements.
"""
import copy
import hashlib
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from SRC.constants import PARTIES
from SRC.forecast_params import validate
from SRC.primary_pipeline import build_projected_primaries, params_for_scenario
from SRC.transform import build_primary_vote_table
from SRC.irv import run_irv_all


def engine_source_hash():
    root = Path(__file__).resolve().parent
    files = ('forecast_engine.py','forecast_params.py','primary_pipeline.py',
             'legacy_primary_model.py','preference_engine.py','irv.py')
    return hashlib.sha256(b''.join((root/name).read_bytes() for name in files)).hexdigest()


def fingerprint(*inputs):
    return hashlib.sha256(pickle.dumps(('forecast-v1',engine_source_hash(),inputs),protocol=4)).hexdigest()


def simplex(values, total=100.0):
    """Euclidean projection onto the non-negative simplex."""
    x = np.asarray(values,dtype=float)
    if not np.isfinite(x).all():
        raise ValueError('Primary shares must be finite')
    order = np.sort(x)[::-1]
    cumulative = np.cumsum(order)-total
    support = np.nonzero(order-cumulative/np.arange(1,len(x)+1)>0)[0]
    threshold = cumulative[support[-1]]/(support[-1]+1)
    return np.maximum(x-threshold,0)


def draw_targets(targets, settings, rng):
    centre = np.array([float(targets[p]) for p in PARTIES])
    if not np.isfinite(centre).all() or (centre<0).any() or centre.sum()<=0:
        raise ValueError('Central primaries must be finite, non-negative and have a positive total')
    centre = centre/centre.sum()*100
    sd = np.array([settings[f'STATEWIDE_SD_{p}_PP'] for p in PARTIES])
    draw = simplex(centre+rng.normal(size=len(PARTIES))*sd)
    return dict(zip(PARTIES,draw))


def perturb_local_primaries(adjusted, settings, rng):
    if not settings['REGION_PRIMARY_SD_PP'] and not settings['SEAT_PRIMARY_SD_PP']:
        return adjusted.copy()
    base = adjusted[PARTIES].to_numpy(dtype=float)
    if (base<0).any() or not np.isfinite(base).all():
        raise ValueError('Invalid central seat primaries')
    rows = base.sum(axis=1)
    columns = base.sum(axis=0)
    region_names = sorted(adjusted.region.unique())
    regional = {region:rng.normal(0,settings['REGION_PRIMARY_SD_PP'],len(PARTIES))/100
                for region in region_names}
    shock = np.array([regional[region] for region in adjusted.region])
    shock += rng.normal(0,settings['SEAT_PRIMARY_SD_PP']/100,base.shape)
    perturbed = np.where(base>0, np.maximum(base+shock,1e-12),0)
    # Raking preserves the current draw's column totals and every seat total.
    # This does not turn the calculator's equal-seat primary convention into
    # a new turnout-weighted model. Structural zero candidates remain zero.
    for _ in range(2000):
        perturbed *= np.divide(columns,perturbed.sum(axis=0),out=np.zeros_like(columns),where=columns>0)
        perturbed *= (rows/perturbed.sum(axis=1))[:,None]
        if np.max(np.abs(perturbed.sum(axis=0)-columns))<1e-9:
            break
    else:
        raise ValueError('Local primary balancing did not converge; no partial forecast published')
    out = adjusted.copy()
    out[PARTIES] = perturbed
    return out


def draw_model_params(params, targets, settings, seat_classes, rng):
    result = copy.deepcopy(params)
    scalars = result.setdefault('scalar_params',{})
    for key,setting,default,lower,upper in [
        ('ON alpha','ON_ALPHA_SD',.6,.01,2),
        ('ON_PRIMARY_DONOR_STRENGTH','ON_DONOR_STRENGTH_SD',0,0,1),
        ('RETIRING_INCUMBENT_PENALTY_PP','RETIREMENT_EFFECT_SD_PP',1,0,10),
        ('SOPHOMORE_SURGE_BONUS_PP','SOPHOMORE_EFFECT_SD_PP',1,0,10),
    ]:
        # Zero uncertainty leaves the exact active parameter untouched.
        if settings[setting]>0:
            mean = float(scalars.get(key,default))
            scalars[key] = float(np.clip(mean+rng.normal(0,settings[setting]),lower,upper))
    if any(settings[k]>0 for k in ('PREF_GENERIC_LOG_SD','PREF_FEDERAL_LOG_SD',
                                   'PREF_VEC_LOG_SD','PREF_SPECIAL_LOG_SD','PREF_CLASS_ON_LOG_SD')):
        result['_forecast_preference_shocks'] = {
            'settings':settings,
            'origin':{origin:dict(zip(PARTIES,rng.normal(size=len(PARTIES)))) for origin in PARTIES},
            'class_on':{seat_class:float(rng.normal()) for seat_class in sorted(set(seat_classes))}}
    return params_for_scenario(result,targets)


def perturb_preference_flows(diagnostic, origin, seat_class, shocks):
    flows = diagnostic['final_flows']
    basis = diagnostic['basis']
    settings = shocks['settings']
    if basis=='ON special prior':
        scale = settings['PREF_SPECIAL_LOG_SD']
    elif basis=='federal ON evidence trial':
        scale = settings['PREF_FEDERAL_LOG_SD']
    elif 'ON' not in flows and any(s.get('vec_exact_field_matched') for s in diagnostic['stages']):
        scale = settings['PREF_VEC_LOG_SD']
    else:
        scale = settings['PREF_GENERIC_LOG_SD']
    values = {}
    for party,value in flows.items():
        tilt = scale*shocks['origin'].get(origin,{}).get(party,0)
        if party=='ON':
            tilt += settings['PREF_CLASS_ON_LOG_SD']*shocks['class_on'].get(seat_class,0)
        values[party] = float(value)*np.exp(tilt)
    total = sum(values.values())
    return {party:value/total for party,value in values.items()} if total else dict(flows)


def simulate(primary_inputs, matrices, params, posterior, ideology, targets,
             seat_adjustments, settings, progress=None):
    settings = validate(settings)
    districts = list(primary_inputs.district)
    if len(districts)!=88 or len(set(districts))!=88:
        raise ValueError('Lower-house forecast requires 88 unique districts')
    rng = np.random.default_rng(settings['SEED'])
    winner_draws, margin_draws, counts, primaries, alp_2pp = [],[],[],[],[]
    for draw in range(settings['SIMULATIONS']):
        drawn_targets = draw_targets(targets,settings,rng)
        model_params = draw_model_params(params,drawn_targets,settings,primary_inputs.seat_type,rng)
        adjusted,_ = build_projected_primaries(primary_inputs,model_params,drawn_targets,seat_adjustments)
        adjusted = perturb_local_primaries(adjusted,settings,rng)
        result = pd.DataFrame(run_irv_all(build_primary_vote_table(adjusted),matrices,
                                         model_params,posterior,ideology)).set_index('district').loc[districts]
        if len(result)!=88 or result.winner.isna().any() or not result.winner.isin(PARTIES).all():
            raise ValueError('Incomplete draw; no partial probabilities published')
        winners = result.winner.to_numpy()
        winner_draws.append(winners)
        margin_draws.append(result.margin.to_numpy(dtype=float))
        alp_2pp.append(result.ALP_2PP.to_numpy(dtype=float))
        counts.append([int(np.sum(winners==party)) for party in PARTIES])
        primaries.append([drawn_targets[p] for p in PARTIES])
        if progress is not None:
            progress(draw+1,settings['SIMULATIONS'])
    winners = np.array(winner_draws)
    count_frame = pd.DataFrame(counts,columns=PARTIES)
    n = len(count_frame)
    seat_rows = []
    for i,seat in enumerate(districts):
        rates = {party:float(np.mean(winners[:,i]==party)) for party in PARTIES}
        row = {'Seat':seat,**{party+' win (%)':100*rate for party,rate in rates.items()},
               'Median winner margin (pp above 50)':100*float(np.median(np.array(margin_draws)[:,i])),
               'Median forced ALP–LNP 2PP (%)':100*float(np.median(np.array(alp_2pp)[:,i])),
               'Largest MC standard error (pp)':100*max(np.sqrt(p*(1-p)/n) for p in rates.values())}
        seat_rows.append(row)
    party_rows = []
    for party in PARTIES:
        seats = count_frame[party]
        qs = np.quantile(seats,[settings['LOWER_QUANTILE'],.25,.5,.75,settings['UPPER_QUANTILE']],method='nearest')
        party_rows.append({'Party':party,'Lower seats':int(qs[0]),'25th percentile':int(qs[1]),
            'Median seats':int(qs[2]),'75th percentile':int(qs[3]),'Upper seats':int(qs[4]),
            'Majority (%)':100*float(np.mean(seats>=45))})
    events = {party+' majority':count_frame[party]>=45 for party in PARTIES}
    events['Hung parliament (no single-party majority)'] = (count_frame.max(axis=1)<45)
    events['LNP + ON jointly reach 45 (overlaps other events)'] = count_frame.LNP+count_frame.ON>=45
    events['LNP + ON reach 45; neither alone (not a formation prediction)'] = (
        (count_frame.LNP+count_frame.ON>=45)&(count_frame.LNP<45)&(count_frame.ON<45))
    government = pd.DataFrame([{'Event':label,'Probability (%)':100*float(np.mean(event)),
        'MC standard error (pp)':100*float(np.sqrt(np.mean(event)*(1-np.mean(event))/n))}
        for label,event in events.items()])
    count_frame.insert(0,'Draw',np.arange(1,n+1))
    return {'seats':pd.DataFrame(seat_rows),'parties':pd.DataFrame(party_rows),
            'government':government,'draws':count_frame,
            'primary_draws':pd.DataFrame(primaries,columns=PARTIES),'settings':settings,
            'central_targets':dict(targets)}
