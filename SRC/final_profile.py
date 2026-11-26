"""Native final v7: owner-approved fitted vectors and separate OTH ballot count.

No website runtime adapter is imported. Numerical counter/allocation are identical
copies of the versioned forecast path and tested draw by draw. Legacy bypasses it.
"""
import copy,json,re
from pathlib import Path
import numpy as np
import pandas as pd
P=['ALP','LNP','GRN','ON','IND','OTH']
CONFIG=json.loads(Path(__file__).with_name('final-profile.json').read_text())
PROFILE_ID=CONFIG['id']
KEY='_website_final_release_profile'
ALLOCATIONS={}

def configure_field(config):
    config=copy.deepcopy(config)
    for review in CONFIG.get('reviewed_candidates',[]):
        found=[c for c in config['candidates'] if c['district']==review['district'] and c['model_group']==review['model_group']]
        if len(found)!=1 or found[0]['candidate_id']!=review['candidate_id']:raise ValueError('Reviewed successor must match exactly one existing candidate')
        found[0].update(kind=review['kind'],median=review['median_pp']/100,low=review['p10_pp']/100,high=review['p90_pp']/100,prior_vote=review['prior_vote_pp']/100)
    return config


def canon(x):
    t = str(x).lower().strip()
    if t in ('', 'no registered party'):
        return 'unaffiliated'
    if 'family first' in t:
        return 'family first'
    if 'dlp' in t or 'democratic labour' in t:
        return 'dlp'
    if 'libertarian' in t or 'liberal democrats' in t:
        return 'liberal democrats'
    if 'shooters' in t:
        return 'shooters fishers farmers'
    return re.sub('[^a-z0-9]+', ' ', t).strip()

def namekey(s):
    return ' '.join(sorted(re.findall('[A-Z]+', str(s).upper())))

class Allocation:

    def __init__(self, root):
        root = Path(root)
        self.ballot = pd.read_csv(root / 'data/development/candidate_field/BALLOT.csv').fillna('')
        review = pd.read_csv(root / 'data/development/candidate_field/REVIEWED_CANDIDATES.csv').fillna('')
        h = pd.read_csv(root / 'data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv').fillna('')
        h = h[h.Electorate != 'Narracan'].copy()
        h['party_key'] = h.OfficialParty.map(canon)
        formal = h.groupby('Electorate').PrimaryVotes.sum()
        h['share'] = h.PrimaryVotes / h.Electorate.map(formal)
        self.median = float(h[h.BroadCategory.eq('OTH')].share.median())
        assert self.median > 0
        state = h.groupby('party_key').PrimaryVotes.sum() / h.PrimaryVotes.sum()
        self.rosters = {}
        self.records = []
        for seat, b in self.ballot.groupby('district'):
            rows = []
            named = review[(review.district == seat) & review.model_group.eq('OTH')]
            matched = {}
            for r in named.to_dict('records'):
                candidates = b[b.model_group.eq('OTH')]
                exact = candidates[candidates.candidate_name.map(namekey) == namekey(r['candidate_name'])]
                if len(exact) != 1 and (r['brand'] == 'West' or '_west' in r['candidate_id']):
                    exact = candidates[candidates.affiliation.eq('The West Party')]
                if len(exact) != 1:
                    raise ValueError(('Unmatched reviewed OTH profile', seat, r['candidate_id']))
                matched[exact.iloc[0].candidate_name] = r['candidate_id']
            for r in b[b.model_group.eq('OTH')].to_dict('records'):
                party = canon(r['affiliation'])
                local = h[(h.Electorate == seat) & h.party_key.eq(party)]
                if r['candidate_name'] in matched:
                    kind = 'reviewed_profile'
                    weight = None
                    source = matched[r['candidate_name']]
                elif party == 'unaffiliated':
                    own = local[local.CandidateName.map(namekey) == namekey(r['candidate_name'])]
                    if len(own):
                        kind = 'local_2022'
                        weight = float(own.share.sum())
                        source = 'Exact returning unaffiliated candidate2022 share'
                    else:
                        kind = 'new_party_median'
                        weight = self.median
                        source = 'Unprofiled/unmatched unaffiliated candidate: no party identity to inherit'
                elif len(local):
                    kind = 'local_2022'
                    weight = float(local.share.sum())
                    source = '2022 local party primary share'
                elif party in state.index:
                    kind = 'statewide_2022'
                    weight = float(state[party])
                    source = '2022 statewide party primary share (87 Nov2022 districts, Narracan excluded)'
                else:
                    kind = 'new_party_median'
                    weight = self.median
                    source = '2022 OTH-candidate median district share for new/unmatched party'
                entry = dict(seat=seat, candidate=r['candidate_name'], affiliation=r['affiliation'], party_key=party, allocation_source=kind, raw_static_weight=weight, profile_id=matched.get(r['candidate_name'], ''), source=source)
                rows.append(entry)
                self.records.append(entry)
            self.rosters[seat] = rows

    def shares(self, seat, primary, profile_amounts):
        rows = self.rosters[seat]
        weights = []
        for r in rows:
            w = profile_amounts[seat, r['profile_id']] if r['allocation_source'] == 'reviewed_profile' else r['raw_static_weight']
            weights.append(w)
        weights = np.asarray(weights, float)
        assert np.all(weights >= 0)
        if primary > 0:
            assert len(rows) > 0 and weights.sum() > 0
        return (primary * weights / weights.sum() if len(weights) and weights.sum() > 0 else np.zeros(len(rows)), weights)

def split_count(seat, params, env, allocation, profiles, trace=False, forced=None):
    rows = allocation.rosters[seat['district']]
    scoped = params
    matrix = env['matrices'][seat['district'].upper()]['matrix']
    if len(rows) < 2:
        if forced:
            return env['forced'](district_votes={p:seat[p] for p in P}, matrix=matrix, seat_type=seat['seat_type'], params=scoped, posterior=env['posterior'], ideology=env['ideology'], party_a=forced[0], party_b=forced[1])
        result = env['engine'].run_irv_for_district(district_votes={p: seat[p] for p in P}, matrix=matrix, seat_type=seat['seat_type'], params=scoped, posterior=env['posterior'], ideology=env['ideology'])
        result['winner_candidate'] = rows[0]['candidate'] if result['winner'] == 'OTH' and rows else result['winner']
        result['runner_up_candidate'] = rows[0]['candidate'] if result['runner_up'] == 'OTH' and rows else result['runner_up']
        return result
    shares, weights = allocation.shares(seat['district'], float(seat['OTH']), profiles)
    names = []
    groups = []
    initial = []
    receiving = []
    for i, p in enumerate(P):
        if p == 'OTH':
            for r, share, weight in zip(rows, shares, weights):
                names.append(r['candidate'])
                groups.append(i)
                initial.append(share)
                receiving.append(weight)
        else:
            names.append(p)
            groups.append(i)
            initial.append(float(seat[p]))
            receiving.append(1.0)
    groups = np.array(groups)
    initial = np.array(initial)
    receiving = np.array(receiving)
    n = len(initial)
    parcels = np.zeros((n, 6))
    parcels[np.arange(n), groups] = initial
    alive = [i for i in range(n) if initial[i] > 0]
    protected = [int(np.where(groups == P.index(p))[0][0]) for p in forced] if forced else []
    for index in protected:
        if index not in alive: alive.append(index)
    totals = initial.copy()
    cache = {}
    events = []
    same_group_queries = 0
    from SRC.irv import parcel_origin_retention
    retention = parcel_origin_retention(scoped)

    def diag(origin, activegroups):
        nonlocal same_group_queries
        key = (origin, tuple(activegroups))
        if key not in cache:
            d = env['pe'].diagnose_preference_weights(P[origin], [P[g] for g in activegroups], matrix, seat['seat_type'], scoped, env['posterior'], env['ideology'])
            cache[key] = (np.array([d['final_flows'].get(p, 0.0) for p in P]), d['basis'])
            if origin == 5 and 5 in activegroups:
                same_group_queries += 1
        return cache[key]
    while len(alive) > 2:
        holder = min([j for j in alive if j not in protected], key=lambda j: (totals[j], j))
        alive.remove(holder)
        active = np.array(alive)
        activegroups = sorted(set(groups[active]))
        hgroup = int(groups[holder])
        hflow, basis = diag(hgroup, activegroups)
        outgoing = parcels[holder].copy()
        parcels[holder] = 0
        denominators = np.bincount(groups[active], weights=receiving[active], minlength=6)
        coeff = receiving[active] / denominators[groups[active]]
        transfer = np.zeros((len(active), 6))
        for origin in np.flatnonzero(outgoing > 0):
            f = hflow
            if origin != hgroup and retention > 0 and (basis != 'ON special prior'):
                f = (1 - retention) * hflow + retention * diag(int(origin), activegroups)[0]
            transfer[:, origin] = outgoing[origin] * f[groups[active]] * coeff
        assert abs(transfer.sum() - outgoing.sum()) < 1e-10
        parcels[active] += transfer
        totals = parcels.sum(axis=1)
        if trace:
            events.append(dict(eliminated=names[holder], eliminated_group=P[hgroup], basis_runtime_control_only=basis, continuing_candidates=[names[i] for i in alive], totals={names[i]: float(totals[i]) for i in alive}))
        assert abs(totals.sum() - initial.sum()) < 1e-09
    ordered = sorted(alive, key=lambda i: (-totals[i], i))
    winner, runner = ordered
    total = totals[winner] + totals[runner]
    result = dict(winner=P[groups[winner]], runner_up=P[groups[runner]], winner_candidate=names[winner], runner_up_candidate=names[runner], winner_pct=float(totals[winner] / total), runner_up_pct=float(totals[runner] / total), margin=float(totals[winner] / total - 0.5), matchup=f'{P[groups[winner]]}-{P[groups[runner]]}', OTH_primary_allocation={r['candidate']: float(v) for r, v in zip(rows, shares)}, same_group_kernel_queries=same_group_queries, trace=events)
    result.update(candidate_groups={names[i]:P[groups[i]] for i in range(n)}, primary_votes=dict(zip(names,map(float,initial))), trace=[r['totals'] for r in events], elimination_order='>'.join(r['eliminated'] for r in events))
    if forced:
        total=sum(totals[i] for i in protected)
        result.update({p+'_2pp':float(totals[i]/total) if total else 0. for p,i in zip(forced,protected)})
        result['forced_2pp_elimination_order']=result['elimination_order']
    return result

def allocation():
 from SRC.candidate_field import ROOT
 key=str(ROOT)
 if key not in ALLOCATIONS:ALLOCATIONS[key]=Allocation(ROOT)
 return ALLOCATIONS[key]

def attach_context(adjusted):
    out=adjusted.copy()
    out.attrs=copy.deepcopy(adjusted.attrs)
    profiles=out.attrs['candidate_field']['candidates']
    out.attrs['candidate_context']=dict(
        effects=[],field=[],profiles=profiles,
        diagnostics=[dict(district=s) for s,rows in allocation().rosters.items() if len(rows)>=2],
        profile_id=PROFILE_ID)
    return out

def count_seat(seat,params,matrix,posterior,ideology,profiles,*,trace=False,forced=None,allocator=None):
    from SRC import preference_engine as pe, irv
    env=dict(pe=pe,engine=irv,forced=irv.run_forced_2pp_for_district,
             matrices={seat['district'].upper():dict(matrix=matrix)},posterior=posterior,ideology=ideology)
    return split_count(seat,params,env,allocator or allocation(),profiles,trace=trace,forced=forced)

def fitted_flows(result,origin,alive,params):
    if params.get(KEY)!=PROFILE_ID:return result
    entry=next((r for r in CONFIG['groups'] if r['origin']==origin and r['alive_set']=='+'.join(sorted(alive))),None)
    if entry:
        weights={p:v*np.exp(entry['offsets'].get(p,0.)) for p,v in result['final_flows'].items()}
        total=sum(weights.values());flows={p:v/total for p,v in weights.items()}
        result=dict(result,final_flows=flows,final_vector=[flows.get(p,0.) for p in P])
    return result

def count_named(seat,context,matrix,params,posterior,ideology):
    amounts={(r['district'],r['candidate_id']):r['realised'] for r in context['profiles']}
    result=count_seat(seat,params,matrix,posterior,ideology,amounts,trace=True)
    result.update({k:seat[k] for k in ('district','region','held_by','seat_type') if k in seat})
    for pair,keys in [(('ALP','LNP'),('ALP_2PP','LNP_2PP')),(('ALP','ON'),('ALP_ON_2CP','ON_ALP_2CP'))]:
        forced=count_seat(seat,params,matrix,posterior,ideology,amounts,forced=pair)
        result.update({key:forced[p+'_2pp'] for p,key in zip(pair,keys)})
    return result
