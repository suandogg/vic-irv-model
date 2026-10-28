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
from SRC.lnp_precollapse_loader import load_lnp_precollapse_inputs, compile_lnp_precollapse
from SRC.irv import run_irv_for_district, run_forced_2pp_for_district, district_key
from SRC.forecast_patterns import balance_primary_pattern,concentration_pattern

STRUCTURAL_EXPERIMENTS = {
    'Current':{},
    'Preference split':{'local_preference_mode':'split'},
    'Preference added':{'local_preference_mode':'add'},
    'Heavy tails t5':{'local_primary_t_df':5},
    'Added preferences + t5':{'local_preference_mode':'add','local_primary_t_df':5},
    'Regional preference patterns':{'preference_region_share':.25,'preference_local_share':.25},
    'All-party concentration patterns':{'concentration_log_sd':.2},
    'Concentration + regional preferences':{'concentration_log_sd':.2,
        'preference_region_share':.25,'preference_local_share':.25},
    'Structured nowcast (development)':{'structured_nowcast':{}},
    'Concentration + structured nowcast (development)':{
        'structured_nowcast':{},'concentration_log_sd':.3,
        'concentration_form':'positive_bounded'},
}


def draw_preference_pattern(shocks, primary_inputs, regional_share, local_share,
                            rng, subregions=None, subregion_fraction=0.):
    """Partition existing origin/recipient variance; retain class-ON separately."""
    shared = np.array([[shocks['origin'][o][p] for p in PARTIES] for o in PARTIES])
    shape = shared.shape
    upper = {r:rng.normal(size=shape) for r in sorted(primary_inputs.region.unique())}
    lower = {r:rng.normal(size=shape) for r in sorted(set(subregions.values()))} if subregion_fraction else {}
    seats = {}
    for seat in primary_inputs.sort_values('district').itertuples():
        geographic = upper[seat.region]
        if subregion_fraction:
            geographic = np.sqrt(1-subregion_fraction)*geographic + np.sqrt(subregion_fraction)*lower[subregions[seat.district]]
        seats[seat.district] = (np.sqrt(1-regional_share-local_share)*shared
            +np.sqrt(regional_share)*geographic+np.sqrt(local_share)*rng.normal(size=shape))
    return seats


def forecast_counts(adjusted, matrices, params, posterior, ideology):
    """Same statutory count; omit unused alternate 2CP and dataframe reshaping."""
    # Scoped to this count only: never reused across draws, settings or evidence.
    params = dict(params)
    params['_forecast_flow_cache'] = {}
    rows = []
    for seat in adjusted.to_dict('records'):
        votes = {party:seat[party] for party in PARTIES}
        matrix = matrices[district_key(seat['district'])]['matrix']
        seat_params = params
        local = params.get('_forecast_local_preference',{}).get(seat['district'])
        patterned = params.get('_forecast_origin_by_seat',{}).get(seat['district'])
        if patterned is not None and '_forecast_preference_shocks' in params:
            seat_params = dict(params)
            shocks = dict(params['_forecast_preference_shocks'])
            shocks['origin'] = {origin:dict(zip(PARTIES,patterned[i])) for i,origin in enumerate(PARTIES)}
            seat_params['_forecast_preference_shocks'] = shocks
            seat_params['_forecast_flow_cache'] = {}
        elif local is not None and '_forecast_preference_shocks' in params:
            seat_params = dict(params)
            shocks = dict(params['_forecast_preference_shocks'])
            split = params.get('_forecast_local_preference_mode')=='split'
            shared_weight,local_weight = (np.sqrt(.5),np.sqrt(.5)) if split else (1.,1.)
            shocks['origin'] = {origin:{party:shared_weight*shocks['origin'][origin][party]
                +local_weight*local[i,j] for j,party in enumerate(PARTIES)}
                for i,origin in enumerate(PARTIES)}
            seat_params['_forecast_preference_shocks'] = shocks
            # Local flows must never leak between districts sharing a matrix.
            seat_params['_forecast_flow_cache'] = {}
        args = dict(district_votes=votes, matrix=matrix, seat_type=seat['seat_type'],
                    params=seat_params, posterior=posterior, ideology=ideology)
        result = run_irv_for_district(**args)
        if {result['winner'],result['runner_up']} == {'ALP','LNP'}:
            # Neither protected party was removed, so the forced count follows
            # exactly the same eliminations and parcel transfers. Reuse it.
            final = result['final_votes']
            total = final['ALP'] + final['LNP']
            alp_2pp = final['ALP']/total if total else 0
        else:
            forced = run_forced_2pp_for_district(**args, party_a='ALP', party_b='LNP')
            alp_2pp = forced['ALP_2pp']
        rows.append(dict(district=seat['district'], winner=result['winner'],
                         margin=result['margin'], ALP_2PP=alp_2pp))
    return pd.DataFrame(rows)


def government_events(count_frame):
    events = {'ALP Majority': count_frame.ALP>=45}
    events['ALP minority'] = (
        (count_frame.ALP<45) & ((count_frame.ALP+count_frame.GRN>=45) |
                               (count_frame.ALP+count_frame.IND>=45)))
    events['LNP majority'] = count_frame.LNP>=45
    joint = (count_frame.LNP+count_frame.ON>=45) & (count_frame.LNP<45) & (count_frame.ON<45)
    events['LNP-ON Majority (LNP-led)'] = joint & (count_frame.LNP>count_frame.ON)
    events['ON-LNP Majority (ON-led)'] = joint & (count_frame.ON>count_frame.LNP)
    events['ON Majority'] = count_frame.ON>=45
    events['Deadlock'] = (
        (count_frame.ALP+count_frame.GRN==44) & (count_frame.LNP+count_frame.ON==44))
    events['Hung parliament'] = count_frame[PARTIES].max(axis=1)<45
    events['Majority'] = count_frame[PARTIES].max(axis=1)>=45
    return events


def uncertainty_profile(settings, multiplier):
    """Sensitivity experiment only: preserve central inputs, seed and draw count."""
    return validate({key:value*multiplier if '_SD' in key else value
                     for key,value in settings.items()})


def binomial_interval(rate, n, z=1.96):
    """Wilson interval: Monte Carlo precision only, including zero/all wins."""
    denominator = 1+z*z/n
    centre = (rate+z*z/(2*n))/denominator
    half = z*np.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/denominator
    return max(0.,centre-half),min(1.,centre+half)


def engine_source_hash():
    root = Path(__file__).resolve().parent
    files = ('forecast_engine.py','forecast_params.py','nowcast_uncertainty.py','nowcast_loader.py','primary_pipeline.py',
             'legacy_primary_model.py','lnp_precollapse_loader.py','preference_engine.py','irv.py','forecast_subregions.py','forecast_patterns.py')
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


def perturb_local_primaries(adjusted, settings, rng, tail_rng=None, tail_df=None,
                            subregions=None, subregion_fraction=0., subregion_rng=None):
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
    if subregion_fraction>0:
        groups = [subregions[seat] for seat in adjusted.district]
        subgroup_shocks = {group:subregion_rng.normal(0,settings['REGION_PRIMARY_SD_PP'],len(PARTIES))/100
                           for group in sorted(set(groups))}
        shock = np.sqrt(1-subregion_fraction)*shock + np.sqrt(subregion_fraction)*np.array(
            [subgroup_shocks[group] for group in groups])
    local = rng.normal(0,settings['SEAT_PRIMARY_SD_PP']/100,base.shape)
    if tail_df is not None:
        # Normal/chi-square mixture: t errors with the SAME pre-balancing variance.
        # Extra randomness uses a separate stream; baseline draws stay paired.
        local *= np.sqrt((tail_df-2)/tail_rng.chisquare(tail_df,base.shape))
    shock += local
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
        source = 'special'
    elif basis=='federal ON evidence trial':
        scale = settings['PREF_FEDERAL_LOG_SD']
        source = 'federal'
    elif 'ON' not in flows and any(s.get('vec_exact_field_matched') for s in diagnostic['stages']):
        scale = settings['PREF_VEC_LOG_SD']
        source = 'vec'
    else:
        scale = settings['PREF_GENERIC_LOG_SD']
        source = 'generic'
    values = {}
    for party,value in flows.items():
        tilt = scale*shocks['origin'].get(origin,{}).get(party,0)
        if party=='ON':
            tilt += settings['PREF_CLASS_ON_LOG_SD']*shocks['class_on'].get(seat_class,0)
        tilt += shocks.get('transport',{}).get(source,{}).get(origin,{}).get(party,0)
        values[party] = float(value)*np.exp(tilt)
    total = sum(values.values())
    return {party:value/total for party,value in values.items()} if total else dict(flows)


def simulate(primary_inputs, matrices, params, posterior, ideology, targets,
             seat_adjustments, settings, progress=None, experiment=None, subregions=None):
    settings = validate(settings)
    experiment = {} if experiment is None else dict(experiment)
    if set(experiment)-{'local_preference_mode','local_primary_t_df','subregion_fraction',
                       'concentration_log_sd','concentration_by_party','concentration_form',
                       'preference_region_share','preference_local_share','structured_nowcast'}:
        raise ValueError('Unknown forecast experiment')
    mode = experiment.get('local_preference_mode')
    if mode not in (None,'split','add'):
        raise ValueError('Local preference experiment must be split or add')
    tail_df = experiment.get('local_primary_t_df')
    if tail_df is not None and (not np.isfinite(tail_df) or tail_df<=2):
        raise ValueError('Variance-matched t experiment requires df > 2')
    concentration_sd = float(experiment.get('concentration_log_sd',0))
    concentration_form = experiment.get('concentration_form','linear')
    if concentration_form not in ('linear','positive_softplus','positive_bounded'):
        raise ValueError('Unknown concentration mapping')
    region_share = float(experiment.get('preference_region_share',0))
    local_share = float(experiment.get('preference_local_share',0))
    if not np.isfinite(concentration_sd) or not 0<=concentration_sd<=1:
        raise ValueError('Concentration stress SD must be between 0 and 1')
    overrides = experiment.get('concentration_by_party',{})
    if not isinstance(overrides,dict) or set(overrides)-set(PARTIES):
        raise ValueError('Party concentration overrides must name only valid party codes')
    concentration_sds = np.array([float(overrides.get(p,concentration_sd)) for p in PARTIES])
    if not np.isfinite(concentration_sds).all() or (concentration_sds<0).any() or (concentration_sds>1).any():
        raise ValueError('Every party concentration SD must be between 0 and 1')
    if not np.isfinite([region_share,local_share]).all() or min(region_share,local_share)<0 or region_share+local_share>1:
        raise ValueError('Preference variance fractions must be nonnegative and sum to at most 1')
    if mode is not None and region_share+local_share>0:
        raise ValueError('Do not stack two local preference variance models')
    districts = list(primary_inputs.district)
    if len(districts)!=88 or len(set(districts))!=88:
        raise ValueError('Lower-house forecast requires 88 unique districts')
    nowcast = experiment.get('structured_nowcast')
    if nowcast is not None:
        from SRC.nowcast_uncertainty import validate_config
        nowcast = validate_config(nowcast,districts)
        experiment['structured_nowcast'] = nowcast
        # Concentration changes the statewide spatial pattern; the structured
        # budget supplies residual district/region errors around that pattern.
        # It REPLACES ordinary residuals, so those are never applied twice.
        if mode is not None or tail_df is not None:
            raise ValueError('Structured nowcast supplies local-noise shape; do not stack local-noise trials')
    sub_fraction = float(experiment.get('subregion_fraction',0))
    if not np.isfinite(sub_fraction) or not 0<=sub_fraction<=1:
        raise ValueError('Subregion variance fraction must be between 0 and 1')
    if sub_fraction>0 and (subregions is None or set(subregions)!=set(districts) or
                           any(not isinstance(v,str) or not v.strip() for v in subregions.values())):
        raise ValueError('Selected subregion trial requires a complete validated district mapping')
    rng = np.random.default_rng(settings['SEED'])
    winner_draws, margin_draws, counts, primaries, alp_2pp, seat_primaries = [],[],[],[],[],[]
    coefficient_draws = []
    exponent_draws = []
    # Snapshot static inputs once per run; no cross-run cache, so Sheet refreshes
    # still take effect on the next forecast.
    lnp_precollapse_inputs = compile_lnp_precollapse(districts,load_lnp_precollapse_inputs())
    for draw in range(settings['SIMULATIONS']):
        drawn_targets = draw_targets(targets,settings,rng)
        model_params = draw_model_params(params,drawn_targets,settings,primary_inputs.seat_type,rng)
        if nowcast is not None and any(nowcast['transport_log_sd'].values()):
            from SRC.nowcast_uncertainty import draw_transport
            transport_rng = np.random.default_rng(np.random.SeedSequence([settings['SEED'],draw,606]))
            shocks = model_params.setdefault('_forecast_preference_shocks',{
                'settings':settings,'origin':{},'class_on':{}})
            shocks['transport'] = draw_transport(nowcast,transport_rng)
        if concentration_sds[PARTIES.index('ON')]>0:
            # Replace ON concentration uncertainty, do not stack it. Its old
            # RNG draw was still consumed to preserve the paired baseline stream.
            model_params['scalar_params']['ON alpha'] = float(params.get('scalar_params',{}).get('ON alpha',.6))
        if region_share+local_share>0 and '_forecast_preference_shocks' in model_params:
            preference_rng = np.random.default_rng(np.random.SeedSequence([settings['SEED'],draw,404]))
            model_params['_forecast_origin_by_seat'] = draw_preference_pattern(
                model_params['_forecast_preference_shocks'],primary_inputs,region_share,local_share,
                preference_rng,subregions,sub_fraction)
        if mode is not None:
            local_rng = np.random.default_rng(np.random.SeedSequence([settings['SEED'],draw,101]))
            model_params['_forecast_local_preference'] = {seat:local_rng.normal(size=(len(PARTIES),len(PARTIES)))
                                                         for seat in sorted(districts)}
            model_params['_forecast_local_preference_mode'] = mode
        adjusted,_ = build_projected_primaries(primary_inputs,model_params,drawn_targets,seat_adjustments,
                                              lnp_precollapse_inputs=lnp_precollapse_inputs,
                                              collect_diagnostics=False)
        coefficients = np.zeros(len(PARTIES))
        exponents = np.ones(len(PARTIES))
        if np.any(concentration_sds):
            pattern_rng = np.random.default_rng(np.random.SeedSequence([settings['SEED'],draw,505]))
            coefficients = pattern_rng.normal(size=len(PARTIES))*concentration_sds
            base = adjusted[PARTIES].to_numpy(dtype=float)
            tilt,exponents = concentration_pattern(base,coefficients,concentration_form)
            adjusted = adjusted.copy()
            adjusted[PARTIES] = balance_primary_pattern(base,tilt)
        coefficient_draws.append(coefficients)
        exponent_draws.append(exponents)
        tail_rng = np.random.default_rng(np.random.SeedSequence([settings['SEED'],draw,202])) if tail_df else None
        sub_rng = np.random.default_rng(np.random.SeedSequence([settings['SEED'],draw,303])) if sub_fraction else None
        if nowcast is None:
            adjusted = perturb_local_primaries(adjusted,settings,rng,tail_rng,tail_df,
                                               subregions,sub_fraction,sub_rng)
        else:
            # Preserve the ordinary stream for later statewide/model draws.
            # Its residuals are consumed but NOT applied; the new budget replaces them.
            if settings['REGION_PRIMARY_SD_PP'] or settings['SEAT_PRIMARY_SD_PP']:
                rng.normal(0,settings['REGION_PRIMARY_SD_PP']/100,
                           (len(adjusted.region.unique()),len(PARTIES)))
                rng.normal(0,settings['SEAT_PRIMARY_SD_PP']/100,(len(adjusted),len(PARTIES)))
            from SRC.nowcast_uncertainty import perturb_district_leans
            lean_rng = np.random.default_rng(np.random.SeedSequence([settings['SEED'],draw,707]))
            adjusted,_ = perturb_district_leans(adjusted,nowcast,lean_rng,subregions,sub_fraction)
        seat_primaries.append(adjusted.set_index('district').loc[districts,PARTIES].to_numpy(dtype=float))
        result = forecast_counts(adjusted,matrices,model_params,posterior,ideology).set_index('district').loc[districts]
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
    diagnostic_rows = []
    primary_array = np.asarray(seat_primaries)*100
    two_pp = np.asarray(alp_2pp)*100
    for i,seat in enumerate(districts):
        rates = {party:float(np.mean(winners[:,i]==party)) for party in PARTIES}
        leading = max(rates,key=rates.get)
        low,high = binomial_interval(rates[leading],n)
        diagnostic_rows.append({'Seat':seat,'Leading party':leading,
            'Leading win (%)':100*rates[leading], 'At least 98%':rates[leading]>=.98,
            'MC 95% lower (%)':100*low,'MC 95% upper (%)':100*high,
            'ALP–LNP 2PP SD (pp)':float(two_pp[:,i].std()),
            'ALP–LNP 2PP 5th (%)':float(np.quantile(two_pp[:,i],.05)),
            'ALP–LNP 2PP 95th (%)':float(np.quantile(two_pp[:,i],.95)),
            'ON primary SD (pp)':float(primary_array[:,i,PARTIES.index('ON')].std()),
            'ALP primary SD (pp)':float(primary_array[:,i,PARTIES.index('ALP')].std()),
            'Zero-support parties':'+'.join(p for j,p in enumerate(PARTIES) if np.all(primary_array[:,i,j]==0))})
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
            'Median seats':int(qs[2]),'Average seats':float(seats.mean()),
            '75th percentile':int(qs[3]),'Upper seats':int(qs[4]),
            'Majority (%)':100*float(np.mean(seats>=45))})
    events = government_events(count_frame)
    government = pd.DataFrame([{'Event':label,'Probability (%)':100*float(np.mean(event)),
        'MC standard error (pp)':100*float(np.sqrt(np.mean(event)*(1-np.mean(event))/n))}
        for label,event in events.items()])
    count_frame.insert(0,'Draw',np.arange(1,n+1))
    return {'seats':pd.DataFrame(seat_rows),'parties':pd.DataFrame(party_rows),
            'government':government,'draws':count_frame,
            'primary_draws':pd.DataFrame(primaries,columns=PARTIES),'settings':settings,
            'central_targets':dict(targets),'diagnostics':pd.DataFrame(diagnostic_rows),
            'experiment':experiment,'subregions':dict(subregions) if sub_fraction else {},
            'concentration_draws':pd.DataFrame(coefficient_draws,columns=PARTIES),
            'concentration_exponents':pd.DataFrame(exponent_draws,columns=PARTIES),
            'primary_extremes':pd.DataFrame({p+' '+label+' (%)':operation(primary_array[:,:,j],axis=1)
                for j,p in enumerate(PARTIES) for label,operation in [('min',np.min),('max',np.max),('mean',np.mean)]})}
