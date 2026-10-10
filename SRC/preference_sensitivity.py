"""On-demand alternative counts. Never mutate the central forecast or inputs."""
import copy
import pandas as pd
from SRC.constants import PARTIES
from SRC.irv import (run_irv_all, initialise_parcels, parcel_totals,
                     distribute_parcel_holder, parcel_origin_retention)
from SRC.preference_engine import diagnose_preference_weights

SPARSE_KEYS = ('ON|ALP+LNP', 'GRN|ALP+LNP+ON')
CONFIGURATIONS = {
    'Central model': 'Unchanged Main rules and current inputs.',
    'Sparse federal evidence off': 'Zero blend weight for two small federal pools. Endpoint stress, not evidence rejection.',
    'Generic fallback pass-through': 'Route generic prior mass through absent parties, including generic contributions to blends. Assumed rankings, not observed ballots. Special-prior rows unchanged.',
    'Pass-through + sparse evidence off': 'Joint test of generic ranking assumptions and sparse federal blending.',
    'OTH preference depletion off': 'Remove existing generic OTH-to-ON siphon depletion. Primary sourcing unchanged.',
    'Joint architecture stress': 'Pass-through, sparse evidence off and OTH preference depletion off.',
    'Special priors: ON minus 5 pp': 'Transfer five percentage points from ON to the other finalist in configured ALP/ON and LNP/ON special priors.',
    'Special priors: ON plus 5 pp': 'Transfer five percentage points to ON from the other finalist in configured ALP/ON and LNP/ON special priors.',
}


def configure(params, posterior, name):
    if name not in CONFIGURATIONS:
        raise ValueError(f'Unknown sensitivity: {name}')
    p, post = copy.deepcopy(params), copy.deepcopy(posterior)
    if name in ('Generic fallback pass-through', 'Pass-through + sparse evidence off', 'Joint architecture stress'):
        p['scalar_params']['SENSITIVITY_GENERIC_PASS_THROUGH'] = True
    if name in ('Sparse federal evidence off', 'Pass-through + sparse evidence off', 'Joint architecture stress'):
        for key in SPARSE_KEYS:
            if key in post and post[key].get('__federal_on_trial__'):
                post[key]['__reliability__'] = 0
    if name in ('OTH preference depletion off', 'Joint architecture stress'):
        p['scalar_params']['OTH_ON_DONOR_DEPLETION_STRENGTH'] = 0
    if name.startswith('Special priors:'):
        delta = -.05 if 'minus' in name else .05
        for key, row in p.get('on_special_scenario_priors', {}).items():
            pair = key.split('|')[0].split('+')
            if set(pair) not in ({'ALP','ON'}, {'LNP','ON'}) or row.get('ON') is None:
                continue
            other = next(party for party in pair if party != 'ON')
            if row.get(other) is None:
                continue
            total = float(row['ON']) + float(row[other])
            if total <= 0:
                continue
            share = min(1, max(0, float(row['ON']) / total + delta))
            row['ON'], row[other] = share, 1-share
    return p, post


def compare(primary, matrices, params, posterior, ideology):
    summary, details = [], []
    reference = None
    for name in CONFIGURATIONS:
        p, post = configure(params, posterior, name)
        result = pd.DataFrame(run_irv_all(primary, matrices, p, post, ideology))
        if reference is None:
            reference = result.copy()
        merged = result.merge(reference[['district','winner','matchup','margin','ALP_2PP']],
                              on='district',suffixes=('','_central'),validate='one_to_one')
        merged['Configuration'] = name
        merged['Winner changed'] = merged.winner.ne(merged.winner_central)
        merged['ALP 2PP change (pp)'] = 100*(merged.ALP_2PP-merged.ALP_2PP_central)
        details.append(merged)
        counts = result.winner.value_counts().to_dict()
        summary.append({'Configuration':name,**{party:int(counts.get(party,0)) for party in PARTIES},
                        'Changed winners':int(merged['Winner changed'].sum()),
                        'Mean seat ALP 2PP (%)':100*result.ALP_2PP.mean()})
    return pd.DataFrame(summary), pd.concat(details,ignore_index=True)


def assumption_rows(primary, matrices, params, posterior, ideology, seat):
    """Expose actual origin parcels; holder-level source labels alone can mislead."""
    group = primary[primary.district.eq(seat)]
    votes = dict(zip(group.party, group.primary_vote))
    parcels = initialise_parcels(votes)
    alive = [party for party in PARTIES if votes.get(party,0)>0]
    matrix, seat_type = matrices[seat.upper()]['matrix'],group.iloc[0].seat_type
    rows, round_no = [], 0
    while len(alive)>2:
        totals = parcel_totals(parcels)
        holder = min(alive,key=lambda party:totals[party])
        field = [party for party in alive if party != holder]
        holder_diag, _, origins = distribute_parcel_holder(parcels,holder,field,matrix,seat_type,params,posterior,ideology)
        round_no += 1
        for origin in origins:
            if 'ON' not in field and holder != 'ON' and origin['origin'] != 'ON':
                continue
            source_origin = origin['origin'] if (parcel_origin_retention(params)>0 and holder_diag['basis']!='ON special prior') else holder
            diagnostic = diagnose_preference_weights(source_origin,field,matrix,seat_type,params,posterior,ideology)
            key = source_origin+'|'+'+'.join(sorted(field))
            record = posterior.get(key,{})
            is_federal = bool(record.get('__federal_on_trial__'))
            mixed = source_origin != holder and parcel_origin_retention(params) < 1
            rows.append({'Seat':seat,'Round':round_no,'Excluded holder':holder,
                'Primary origin':origin['origin'],'Continuing parties':'+'.join(field),
                'Parcel (% of seat)':100*origin['votes'],'Source':diagnostic['basis'] if not mixed else 'Mixed holder/origin: '+holder_diag['basis']+' / '+diagnostic['basis'],
                'Origin retention':parcel_origin_retention(params),
                'Federal evidence seats':record.get('__evidence_seats__') if is_federal else None,
                'Federal blend weight':record.get('__reliability__') if is_federal else None,
                'Evidence limitation':('Federal field-specific reconstruction, not state ballot evidence' if is_federal else
                    'Configured hypothetical final-pair prior' if diagnostic['basis']=='ON special prior' else
                    'Historical non-ON evidence with synthetic ON allocation / generic fallback'),
                **{party+' flow (%)':100*origin.get(party,0) if party in field else None for party in PARTIES}})
        alive = field
    return pd.DataFrame(rows)
