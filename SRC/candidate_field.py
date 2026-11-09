"""Opt-in field-aware candidate layer. All shares at this boundary are fractions.

Rebuilds seats from the ballot instead of treating past independents as seat
lean. A seat with no independent has no IND vote; the whole surface is released
per draw as a share, never as a fixed component. Reviewed candidates then enter
through one attraction model, so entrants compete for the same voters. The
statewide stage restores targets through all seats with no locked districts.

Disabled by default: without an experiment entry this module is never called.
Candidate strengths and donor affinities are provisional priors, not fitted.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from SRC.constants import PARTIES

ROOT = Path(__file__).resolve().parents[1]
FIELD_DIR = ROOT / 'data' / 'development' / 'candidate_field'
IND, OTH = PARTIES.index('IND'), PARTIES.index('OTH')
MAJOR = [i for i, p in enumerate(PARTIES) if p not in ('IND', 'OTH')]
Z90 = 1.2815515655446004


def logit(x):
    return np.log(x/(1-x))


def expit(x):
    return 1/(1+np.exp(-x))


def load_field_config(residual_retention=0.0, residual_mode='combined', donor_set='pooled',
                      directory=None):
    """Compile JSON-safe experiment input from the ballot, strength and donor tables."""
    directory = Path(directory) if directory else FIELD_DIR
    ballot = pd.read_csv(directory/'BALLOT.csv', keep_default_na=False)
    reviewed = pd.read_csv(directory/'REVIEWED_CANDIDATES.csv', keep_default_na=False)
    defaults_path = directory/'DEFAULT_IND_STRENGTHS.csv'
    if defaults_path.exists():
        # Reviewed independents override the data-based default for their seat.
        defaults = pd.read_csv(defaults_path, keep_default_na=False)
        covered = set(reviewed[reviewed.model_group.eq('IND')].district)
        reviewed = pd.concat([reviewed, defaults[~defaults.district.isin(covered)]], ignore_index=True)
    affinity = pd.read_csv(directory/'DONOR_AFFINITY.csv', keep_default_na=False)
    if ballot.duplicated(['district', 'candidate_name']).any():
        raise ValueError('Duplicate candidate on ballot')
    if not ballot.model_group.isin(PARTIES).all():
        raise ValueError('Invalid ballot model group')
    rows = affinity[affinity.donor_set.eq(donor_set)]
    if rows.empty:
        raise ValueError(f'Unknown donor set: {donor_set}')
    return dict(
        residual_retention=float(residual_retention), residual_mode=residual_mode,
        donor_set=donor_set, roster_status=sorted(set(ballot.roster_status)),
        groups={d: sorted(set(g.model_group)) for d, g in ballot.groupby('district')},
        affinity={r.geography: [float(getattr(r, p)) for p in PARTIES] for r in rows.itertuples()},
        candidates=[dict(district=r.district, candidate_id=r.candidate_id, kind=r.kind,
                         model_group=r.model_group, median=float(r.median_pp)/100,
                         low=float(r.p10_pp)/100, high=float(r.p90_pp)/100, brand=r.brand,
                         brand_share=float(r.brand_share or 0),
                         prior_vote=float(r.prior_vote_pp or 0)/100)
                    for r in reviewed.itertuples()])


def require_no_candidate_records(effects):
    """Named candidate records and the field layer must not adjust the same seats."""
    from SRC.candidate_effects import enabled_rows
    if not enabled_rows(effects).empty:
        raise ValueError('Turn off enabled candidate records before using the field-aware layer')


def validate_config(config, districts):
    if not 0 <= float(config['residual_retention']) <= 1:
        raise ValueError('Residual retention must be between 0 and 1')
    if config['residual_mode'] not in ('combined', 'separate'):
        raise ValueError('Unknown residual mode')
    if set(config['groups']) != set(districts):
        raise ValueError('Ballot must cover every district')
    for geography in ('metro', 'nonmetro'):
        vector = np.array(config['affinity'].get(geography, []), dtype=float)
        if vector.shape != (len(PARTIES),) or (vector < 0).any():
            raise ValueError(f'Invalid {geography} donor affinity')
    for c in config['candidates']:
        if c['district'] not in config['groups']:
            raise ValueError(f"Unknown district {c['district']}")
        if c['model_group'] not in config['groups'][c['district']]:
            raise ValueError(f"{c['candidate_id']}: group not on ballot")
        if c['kind'] not in ('entrant', 'switch'):
            raise ValueError(f"{c['candidate_id']}: invalid kind")
        if not 0 < c['low'] <= c['median'] <= c['high'] < 1:
            raise ValueError(f"{c['candidate_id']}: invalid strength interval")
    return config


def sample_strength(candidate, shocks, rng):
    """Logit-normal strength. Candidates sharing a brand share one shock."""
    if rng is None:
        return candidate['median']
    scale = (logit(candidate['high'])-logit(candidate['low']))/(2*Z90)
    weight = candidate['brand_share']
    shock = rng.standard_normal()
    if candidate['brand']:
        shock = np.sqrt(weight)*shocks[candidate['brand']]+np.sqrt(1-weight)*shock
    return float(expit(logit(candidate['median'])+scale*shock))


def release(votes, group, affinity):
    """Move a whole group's vote to the other groups by affinity-weighted size."""
    out = votes.copy()
    amount, out[group] = out[group], 0.
    weights = out*affinity
    if weights.sum() <= 0:
        raise ValueError('Released vote has no eligible destination')
    return out+amount*weights/weights.sum()


def solve_strength(votes, target, affinity):
    """Lambda giving a candidate `target` of the seat when standing alone."""
    if target >= (votes*(affinity > 0)).sum():
        raise ValueError('Candidate strength exceeds available donors')
    low, high = 0., 1e6
    for _ in range(200):
        middle = (low+high)/2
        taken = (votes*affinity*middle/(1+affinity*middle)).sum()
        low, high = (middle, high) if taken < target else (low, middle)
    return (low+high)/2


def enter(votes, entrants, affinity):
    """Joint attraction model. Each origin row sums to one, so seats stay whole.

    Strengths are solo strengths: a second entrant reduces what the first
    receives because both draw on the same origin voters.
    """
    strengths = np.array([solve_strength(votes, e['strength'], affinity) for e in entrants])
    if not len(entrants):
        return votes.copy(), {}
    pull = np.outer(affinity, strengths)
    moved = votes[:, None]*pull/(1+pull.sum(axis=1, keepdims=True))
    out = votes-moved.sum(axis=1)
    realised = {}
    for k, e in enumerate(entrants):
        out[PARTIES.index(e['model_group'])] += moved[:, k].sum()
        realised[e['candidate_id']] = float(moved[:, k].sum())
    return out, realised


def carry_switcher(votes, group, prior_vote, follow_share, affinity):
    """Credit only voters who did not already return to the new party."""
    weights = votes*affinity
    weights = weights/weights.sum()
    uplift = follow_share*(1-weights[group])*prior_vote
    donors = weights.copy()
    donors[group] = 0
    out = votes-uplift*donors/donors.sum()
    out[group] += uplift
    return out, float(uplift)


def scale_column(values, columns, goal):
    """Scale columns to a statewide mean; a party with no vote stays at zero."""
    current = values[:, columns].sum(axis=1).mean()
    if current > 0:
        values[:, columns] *= goal/current


def balance(values, targets, config):
    """Restore statewide means through every seat; true zeros stay zero."""
    target = np.array([float(targets[p]) for p in PARTIES])
    target = target/target.sum()
    residual = target[IND]+target[OTH]
    field = values[:, [IND, OTH]].sum(axis=1).mean()
    combined = config['residual_mode'] == 'combined'
    wanted = field+float(config['residual_retention'])*(residual-field) if combined else residual
    out = values.copy()
    goal = target.copy()
    goal[MAJOR] *= (1-wanted)/(1-residual)
    for _ in range(5000):
        for j in MAJOR:
            scale_column(out, [j], goal[j])
        if combined:
            scale_column(out, [IND, OTH], wanted)
        else:
            scale_column(out, [IND], goal[IND])
            scale_column(out, [OTH], goal[OTH])
        out /= out.sum(axis=1, keepdims=True)
        error = max(np.max(np.abs(out[:, MAJOR].mean(axis=0)-goal[MAJOR])),
                    abs(out[:, [IND, OTH]].sum(axis=1).mean()-wanted))
        if error < 1e-10:
            return out, dict(field_residual=float(field), wanted_residual=float(wanted))
    raise ValueError('Candidate field balancing did not converge')


def apply_candidate_field(current, targets, config, rng=None):
    """Return seat primaries for the ballot. rng=None gives the central case."""
    original = current[PARTIES].to_numpy(dtype=float, copy=True)
    if not np.isfinite(original).all() or (original < 0).any() or not np.allclose(original.sum(axis=1), 1):
        raise ValueError('Invalid baseline primaries')
    brands = sorted({c['brand'] for c in config['candidates'] if c['brand']})
    shocks = {b: rng.standard_normal() for b in brands} if rng is not None else {}
    follow = float(rng.beta(2, 3)) if rng is not None else .4
    drawn = [dict(c, strength=sample_strength(c, shocks, rng)) for c in config['candidates']]
    values = original.copy()
    records = []
    for i, seat in enumerate(current.to_dict('records')):
        district = seat['district']
        field = config['groups'][district]
        metro = 'metro' if 'Metro' in str(seat['region']) else 'nonmetro'
        affinity = np.array(config['affinity'][metro], dtype=float)
        named = [c for c in drawn if c['district'] == district]
        entrants = [c for c in named if c['kind'] == 'entrant']
        votes = values[i].copy()
        # The principal independent, reviewed or default, replaces the old IND
        # surface, so past candidates never pass their vote to a new one.
        if 'IND' not in field or any(c['model_group'] == 'IND' for c in entrants):
            votes = release(votes, IND, affinity)
        if 'OTH' not in field:
            votes = release(votes, OTH, affinity)
        for c in named:
            if c['kind'] == 'switch':
                votes, uplift = carry_switcher(votes, PARTIES.index(c['model_group']),
                                               c['prior_vote'], follow, affinity)
                records.append(dict(district=district, candidate_id=c['candidate_id'], realised=uplift))
        votes, realised = enter(votes, entrants, affinity)
        records.extend(dict(district=district, candidate_id=k, realised=v) for k, v in realised.items())
        if not np.isclose(votes.sum(), 1, atol=1e-9, rtol=0):
            raise ValueError(f'{district}: field stage lost vote share')
        values[i] = votes
    balanced, summary = balance(values, targets, config)
    out = current.copy()
    out[PARTIES] = balanced
    out.attrs['candidate_field'] = dict(summary, candidates=records)
    return out
