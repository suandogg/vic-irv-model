"""Opt-in 2026 Labor-Liberal preference deal. Off by default.

Seat preference rows come from the 2022 count, when the Liberals recommended
the Greens above Labor. For 2026 the Liberals recommend Labor above the Greens
everywhere except Footscray and Brunswick, and Labor issues no recommendation
in Prahran instead of recommending the Greens.

The switch moves only the split between two continuing candidates, on the logit
scale, after the engine has built its central flow. Their combined share, and
every other recipient's share, are unchanged.

Liberal shift, seat by seat, from the logit change in the Liberal flow to Labor
(share of Labor + Greens) between 2018, when the Liberals put the Greens last,
and 2022. tools/build_htv_deal_evidence.py builds the evidence from VEC data only:
  distribution: full 2018 count, only Labor and Greens left (Brunswick,
      Melbourne, Northcote). These seats use their own change, and their mean is
      the pooled shift used for every seat with no 2018 evidence (Richmond).
  distribution_third_candidate (Pascoe Vale, independent still in the 2018
      count) and indicative_2cp (Preston, fitted from voting-centre 2CP counts):
      indirect evidence, so the seat's own change is averaged with the pooled
      shift (INDIRECT_WEIGHT = 0.5, a judgement).

Prahran: there is no open-card evidence. Labor recommended the Greens in both
2018 and 2022, and its flow barely moved (0.11 logit). An open card is treated
as half a reversal of a recommendation: half the pooled Liberal shift, against
the Greens. This is a judgement, not fitted.
"""
import math
from pathlib import Path
import pandas as pd

EVIDENCE = Path(__file__).resolve().parents[1]/'data'/'development'/'HTV_DEAL_EVIDENCE.csv'
EXCEPT = ('Footscray', 'Brunswick')
INDIRECT_WEIGHT = .5


def liberal_rows(path=EVIDENCE):
    rows = pd.read_csv(path)
    return rows[rows.origin.eq('LNP') & rows.toward.eq('ALP') & rows.away.eq('GRN')]


def liberal_shift_from_evidence(path=EVIDENCE):
    rows = liberal_rows(path)
    clean = rows[rows.method.eq('distribution')]
    if clean.empty:
        raise ValueError('No clean 2018-2022 Liberal preference pairs')
    return float(clean.logit_change.mean())


def seat_liberal_shifts(pooled, indirect_weight=INDIRECT_WEIGHT, path=EVIDENCE):
    out = {}
    for r in liberal_rows(path).itertuples():
        weight = 1. if r.method == 'distribution' else indirect_weight
        out[r.District.upper()] = round(weight*r.logit_change+(1-weight)*pooled, 6)
    return out


def load_htv_deal_config(liberal_shift=None, prahran_shift=None, exceptions=EXCEPT,
                         indirect_weight=INDIRECT_WEIGHT, seat_specific=True):
    if liberal_shift is None:
        liberal_shift = liberal_shift_from_evidence()
    if prahran_shift is None:
        prahran_shift = liberal_shift/2
    seats = seat_liberal_shifts(liberal_shift, indirect_weight) if seat_specific else {}
    return validate_config(dict(liberal_shift=float(liberal_shift), prahran_shift=float(prahran_shift),
                                exceptions=sorted(exceptions), seat_liberal_shifts=seats))


def validate_config(config):
    if set(config) != {'liberal_shift', 'prahran_shift', 'exceptions', 'seat_liberal_shifts'}:
        raise ValueError('Unknown preference deal configuration')
    values = [config['liberal_shift'], config['prahran_shift'], *config['seat_liberal_shifts'].values()]
    if not all(math.isfinite(v) and 0 <= v <= 3 for v in values):
        raise ValueError('Preference deal shifts must be between 0 and 3 logits')
    return config


def seat_shifts(district, config):
    """{eliminated party: (toward, away, logit shift)} for one district."""
    name = str(district).strip().upper()
    shifts = {}
    if name not in {e.upper() for e in config['exceptions']}:
        shifts['LNP'] = ('ALP', 'GRN', config['seat_liberal_shifts'].get(name, config['liberal_shift']))
    if name == 'PRAHRAN':
        shifts['ALP'] = ('LNP', 'GRN', config['prahran_shift'])
    return shifts


def apply_htv_deal(matrices, config):
    """Copy of the matrices with each seat's shifts attached. Source rows unchanged."""
    validate_config(config)
    out = {}
    for key, item in matrices.items():
        matrix = dict(item['matrix'])
        # Merge, so other review rules (SRC/htv_review.py) attached to other
        # eliminated parties are kept whichever switch is applied first.
        matrix['__htv_shift__'] = dict(matrix.get('__htv_shift__', {}), **seat_shifts(key, config))
        out[key] = dict(item, matrix=matrix)
    return out


def shift_flows(flows, eliminated, matrix):
    """Move the toward/away split; the pair's combined share and others are unchanged.

    A rule is (toward, away, value) or (toward, away, value, kind):
      logit  (default) add value to the logit of toward's share of the pair;
      share  set toward's share of the pair to value (SRC/htv_review.py);
      points subtract value from toward's share of the pair (SRC/htv_review.py).
    """
    rule = matrix.get('__htv_shift__', {}).get(eliminated)
    if not rule:
        return flows
    toward, away, value = rule[:3]
    kind = rule[3] if len(rule) > 3 else 'logit'
    a, b = flows.get(toward, 0.0), flows.get(away, 0.0)
    total = a+b
    if toward not in flows or away not in flows or total <= 0:
        return flows
    p = min(max(a/total, 1e-9), 1-1e-9)
    if kind == 'logit':
        if value == 0:
            return flows
        p = 1/(1+math.exp(-(math.log(p/(1-p))+value)))
    elif kind == 'share':
        p = value
    elif kind == 'points':
        p = min(max(p-value, 0.), 1.)
    else:
        raise ValueError(f'Unknown preference rule kind: {kind}')
    return dict(flows, **{toward: total*p, away: total*(1-p)})
