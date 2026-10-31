"""Named minor-candidate count for reviewed candidate-effect districts.

Retains Main's group preference engine and locked holder-level ON priors.
Named IND/OTH origins use explicit candidate-recipient prior weights, restricted
to the continuing field. These are provisional priors, not observed rankings.
"""
import numpy as np
import pandas as pd
from SRC.constants import PARTIES
from SRC.loaders import RAW_DIR
from SRC.candidate_effects import enabled_rows, number
from SRC.irv import parcel_origin_retention
from SRC.preference_engine import diagnose_preference_weights

FIELD_COLUMNS = ['district','candidate_id','candidate_name','model_group',
                 'baseline_weight','receiving_weight','preference_profile_id','enabled']
PREF_COLUMNS = ['district','profile_id','recipient_id','weight','enabled']


def load_candidate_tables():
    tables = []
    for name, columns in [('LOWER_CANDIDATE_FIELD',FIELD_COLUMNS),('LOWER_CANDIDATE_PREFS',PREF_COLUMNS)]:
        path = RAW_DIR / (name+'.csv')
        tables.append(pd.read_csv(path).fillna('') if path.exists() else pd.DataFrame(columns=columns))
    return tuple(tables)


def apply_candidate_pipeline(adjusted, targets, seat_adjustments=None, effects=None, rng=None, candidate_tables=None):
    from SRC.candidate_effects import load_candidate_effects, apply_candidate_effects
    effects = load_candidate_effects() if effects is None else effects
    out, diagnostics = apply_candidate_effects(adjusted,effects,targets,seat_adjustments,rng)
    if not diagnostics.empty:
        field,profiles = load_candidate_tables() if candidate_tables is None else candidate_tables
        # Validate the full field before publishing even an adjusted primary.
        for district in diagnostics.district.unique():
            seat = out.loc[out.district.eq(district)].iloc[0].to_dict()
            candidate_primaries(seat,effects,diagnostics[diagnostics.district.eq(district)],field,profiles)
        out.attrs['candidate_context'] = dict(effects=effects.fillna('').to_dict('records'),
            diagnostics=diagnostics.to_dict('records'),field=field.to_dict('records'),profiles=profiles.to_dict('records'))
    return out


def result_from_context(seat, context, matrix, params, posterior, ideology):
    if not context or seat['district'] not in {r['district'] for r in context['diagnostics']}:
        return None
    return seat_candidate_result(seat,*(pd.DataFrame(context[k]) for k in ('effects','diagnostics','field','profiles')),
                                 matrix,params,posterior,ideology)


def candidate_primaries(seat, effects, diagnostics, field, profiles):
    district = seat['district']
    roster = enabled_rows(field)
    roster = roster[roster.district.eq(district)].copy() if not roster.empty else roster
    if roster.empty or roster.candidate_id.duplicated().any() or roster.candidate_id.eq('').any():
        raise ValueError(f'{district}: provide a complete unique LOWER_CANDIDATE_FIELD')
    if not roster.model_group.isin(PARTIES).all():
        raise ValueError(f'{district}: invalid candidate model group')
    roster = roster.sort_values('candidate_id').reset_index(drop=True)
    for p in ['ALP','LNP','GRN','ON']:
        if roster.model_group.eq(p).sum() > 1:
            raise ValueError(f'{district}: multiple {p} nominees need a separate reviewed preference model')
    effect_rows = enabled_rows(effects)
    effect_rows = effect_rows[effect_rows.district.eq(district)]
    additions = dict(zip(diagnostics.candidate_id,diagnostics.realised_effect_pp/100))
    for r in effect_rows.itertuples():
        matches = roster[roster.candidate_id.eq(r.candidate_id)]
        if r.continuity_status == 'retired':
            if not matches.empty:
                raise ValueError(f'{district}: departed candidate appears in current field')
        elif len(matches)!=1 or matches.iloc[0].model_group!=r.current_model_group:
            raise ValueError(f'{district}: current candidate missing or group mismatch: {r.candidate_id}')
        elif str(r.preference_profile_id).strip() and matches.iloc[0].preference_profile_id != r.preference_profile_id:
            raise ValueError(f'{district}: candidate profile mismatch')
    votes = {}
    for p in PARTIES:
        group = roster[roster.model_group.eq(p)]
        added = sum(additions.get(cid,0) for cid in group.candidate_id)
        baseline = float(seat[p])-added
        if baseline < -1e-10 or (float(seat[p])>1e-12 and group.empty):
            raise ValueError(f'{district}: incomplete field or candidate addition exceeds {p}')
        weight = np.array([number(r,'baseline_weight') for _,r in group.iterrows()])
        if baseline>1e-12 and weight.sum()<=0:
            raise ValueError(f'{district}: {p} baseline needs explicit candidate allocation weights')
        for j,(_,r) in enumerate(group.iterrows()):
            number(r,'receiving_weight')
            votes[r.candidate_id] = max(0,baseline)*(weight[j]/weight.sum() if weight.sum() else 0)+additions.get(r.candidate_id,0)
    prefs = enabled_rows(profiles)
    prefs = prefs[prefs.district.eq(district)].copy() if not prefs.empty else prefs
    compiled = {}
    if not prefs.empty:
        if prefs.duplicated(['profile_id','recipient_id']).any():
            raise ValueError(f'{district}: duplicate candidate preference recipient')
        for profile_id, group in prefs.groupby('profile_id'):
            if not str(profile_id).strip() or not set(group.recipient_id).issubset(set(roster.candidate_id)):
                raise ValueError(f'{district}: unknown recipient in profile')
            vector = {r.recipient_id:number(r,'weight') for _,r in group.iterrows()}
            if sum(vector.values())<=0:
                raise ValueError(f'{district}: empty preference profile')
            compiled[profile_id] = vector
    for r in roster.itertuples():
        if r.model_group in ('IND','OTH'):
            if r.preference_profile_id not in compiled:
                raise ValueError(f'{district}: missing explicit profile for {r.candidate_id}')
            if compiled[r.preference_profile_id].get(r.candidate_id,0)>0:
                raise ValueError(f'{district}: candidate preference profile includes self')
        elif r.preference_profile_id:
            raise ValueError(f'{district}: profiles override only IND/OTH; major/ON engine stays authoritative')
    if not np.isclose(sum(votes.values()),1,atol=1e-9,rtol=0):
        raise ValueError(f'{district}: candidate shares do not sum to 100%')
    return roster, votes, compiled


def count_named(roster, primaries, profiles, matrix, seat_type, params, posterior, ideology, forced=None):
    primaries = dict(primaries)
    records = roster.set_index('candidate_id').to_dict('index')
    categories = {cid:r['model_group'] for cid,r in records.items()}
    alive = sorted(cid for cid,v in primaries.items() if v>0)
    protected = []
    if forced:
        for p in forced:
            matches = [cid for cid,g in categories.items() if g==p]
            if not matches:
                # Match the legacy hypothetical 2CP convention. This zero-vote
                # proxy exists only in the forced count, never the real field.
                proxy = '__forced_'+p
                records[proxy] = dict(model_group=p,receiving_weight=1,preference_profile_id='')
                categories[proxy] = p
                primaries[proxy] = 0
                matches = [proxy]
            if len(matches)!=1:
                raise ValueError(f'Forced {forced} count needs exactly one {p} nominee in field')
            protected.extend(matches)
        alive = sorted(set(alive)|set(protected))
    if len(alive)<2:
        raise ValueError('Candidate field has fewer than two active candidates')
    parcels = {cid:{cid:float(primaries.get(cid,0))} for cid in records}
    trace = []
    retention = parcel_origin_retention(params)
    while len(alive)>2:
        totals = {cid:sum(parcels[cid].values()) for cid in records}
        removable = [cid for cid in alive if cid not in protected]
        holder = min(removable,key=lambda cid:(totals[cid],cid))
        alive.remove(holder)
        groups = sorted(set(categories[cid] for cid in alive))
        def flow(origin):
            record = records[origin]
            if record['model_group'] in ('IND','OTH'):
                vector = profiles[record['preference_profile_id']]
                total = sum(vector.get(cid,0) for cid in alive)
                if total<=0:
                    raise ValueError(f'Profile {record["preference_profile_id"]} has no continuing support')
                return {cid:vector.get(cid,0)/total for cid in alive},'explicit candidate prior'
            diag = diagnose_preference_weights(categories[origin],groups,matrix,seat_type,params,posterior,ideology)
            vector = {}
            for group,share in diag['final_flows'].items():
                recipients = [cid for cid in alive if categories[cid]==group]
                total = sum(float(records[cid]['receiving_weight']) for cid in recipients)
                if share>0 and total<=0:
                    raise ValueError(f'No receiving weights for continuing {group}')
                for cid in recipients:
                    vector[cid] = share*float(records[cid]['receiving_weight'])/total if total else 0
            return vector,diag['basis']
        holder_flow,basis = flow(holder)
        outgoing = parcels[holder]
        parcels[holder] = {}
        for origin,amount in outgoing.items():
            if amount<=0:
                continue
            vector = holder_flow
            if origin!=holder and retention>0 and basis!='ON special prior':
                origin_flow,_ = flow(origin)
                vector = {cid:(1-retention)*holder_flow.get(cid,0)+retention*origin_flow.get(cid,0) for cid in alive}
            if not np.isclose(sum(vector.values()),1,atol=1e-9,rtol=0):
                raise ValueError('Candidate preference flow does not sum to one')
            for cid in alive:
                parcels[cid][origin] = parcels[cid].get(origin,0)+amount*vector.get(cid,0)
        totals = {cid:sum(parcels[cid].values()) for cid in records}
        if not np.isclose(sum(totals.values()),sum(primaries.values()),atol=1e-9,rtol=0):
            raise ValueError('Candidate parcel conservation failure')
        trace.append(dict(eliminated=holder,basis=basis,**totals))
    totals = {cid:sum(parcels[cid].values()) for cid in records}
    ordered = sorted(alive,key=lambda cid:(-totals[cid],cid))
    total = sum(totals[cid] for cid in ordered)
    winner,runner = ordered
    return dict(winner=categories[winner],runner_up=categories[runner],
                winner_candidate=winner,runner_up_candidate=runner,
                winner_pct=totals[winner]/total,runner_up_pct=totals[runner]/total,
                margin=totals[winner]/total-.5,matchup=f'{categories[winner]}-{categories[runner]}',
                elimination_order='>'.join(r['eliminated'] for r in trace),
                final_votes=totals,candidate_groups=categories,trace=trace,primary_votes=primaries)


def seat_candidate_result(seat, effects, diagnostics, field, profiles, matrix, params, posterior, ideology):
    district = seat['district']
    diag = diagnostics[diagnostics.district.eq(district)]
    roster, primaries, priors = candidate_primaries(seat,effects,diag,field,profiles)
    args = (roster,primaries,priors,matrix,seat['seat_type'],params,posterior,ideology)
    ordinary = count_named(*args)
    alp_lnp = count_named(*args,forced=('ALP','LNP'))
    alp_on = count_named(*args,forced=('ALP','ON'))
    def protected_share(result,party):
        ids = {cid for cid,group in result['candidate_groups'].items() if group==party}
        return sum(v for cid,v in result['final_votes'].items() if cid in ids)
    alp = protected_share(alp_lnp,'ALP')
    lnp = protected_share(alp_lnp,'LNP')
    a = protected_share(alp_on,'ALP')
    o = protected_share(alp_on,'ON')
    return dict(district=district,region=seat['region'],held_by=seat['held_by'],
                **{k:v for k,v in ordinary.items() if k not in ('final_votes',)},
                ALP_2PP=alp/(alp+lnp),LNP_2PP=lnp/(alp+lnp),
                forced_2pp_elimination_order=alp_lnp['elimination_order'],
                ALP_ON_2CP=a/(a+o),ON_ALP_2CP=o/(a+o),
                forced_alp_on_2cp_elimination_order=alp_on['elimination_order'])
