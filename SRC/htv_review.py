"""Opt-in 2026 how-to-vote review. Off by default.

Three rules, attached to the matrices like SRC/htv_deal.py and applied by its
shift_flows after the engine builds each central flow. Each changes only the
split between two continuing candidates; their combined share, and every other
recipient's share, are unchanged. Parcels keep their primary origin
(PARCEL_ORIGIN_RETENTION = 1), so each rule acts on ballots by first preference.

1. One Nation, Labor v Greens (Inner and Middle Ring seats). Whenever One
   Nation-origin ballots move with Labor and the Greens both in the count,
   Labor's share of the pair is set to ON_TARGET. Every such split uses the same
   share, so One Nation voters' final split in a Labor-Greens contest equals the
   target. Without it the split comes from the ideology prior (57.9% inner,
   60.3% middle ring). Evidence: AEC two-candidate preferred flows of One Nation
   first preferences in Labor-Greens contests, equal-seat average of Melbourne,
   Cooper and Wills, 66.2% in 2022 and 76.8% in 2025 (Melbourne 2022 68.20%
   checked against the AEC page). 72.5% is the middle of a 70-75% band: the
   larger 2026 One Nation vote comes partly from former Liberal voters, and
   Victorian Labor is less popular than federal Labor was in 2025. One Nation's
   2026 card (Labor above the Greens) points the same way; no extra shift is
   added for it, since the federal flows already include its federal card.

2. Greens open cards in 15 seats. The 2022 Greens cards put Labor ahead of the
   Liberals everywhere. In 2026 the Greens recommend only Greens first and One
   Nation last in these seats. Greens-origin ballots moving with Labor and the
   Coalition both in the count give Labor GREENS_POINTS less of the pair. Scale
   from Antony Green's comparison of Greens open-card seats at the 2007 (6.6
   points) and 2010 (about 3 points) elections; observational, not causal. One
   Nation stays last, so Labor v One Nation contests are not changed.

3. Labor open card in Caulfield, treated exactly like Prahran in SRC/htv_deal.py
   (half the pooled 2018-2022 Liberal shift, against the Greens). A judgement.
   Reported by one source only; confirm against the VEC card.
"""
import math
from SRC.htv_deal import load_htv_deal_config

ON_TARGET = .725
ON_SEAT_TYPES = ('INNER RING', 'MIDDLE RING')
GREENS_POINTS = .03
GREENS_SEATS = ('Albert Park', 'Ashwood', 'Bellarine', 'Bendigo East', 'Bendigo West', 'Essendon',
                'Euroa', 'Gippsland East', 'Mildura', 'Mornington', 'Point Cook', 'Polwarth',
                'South Barwon', 'Tarneit', 'Werribee')
LABOR_OPEN_SEATS = ('Caulfield',)
KEYS = {'on_target', 'on_seat_types', 'greens_points', 'greens_seats', 'labor_open_seats', 'labor_open_shift'}


def load_htv_review_config(on_target=ON_TARGET, greens_points=GREENS_POINTS, on_seat_types=ON_SEAT_TYPES,
                           greens_seats=GREENS_SEATS, labor_open_seats=LABOR_OPEN_SEATS, labor_open_shift=None):
    if labor_open_shift is None:
        labor_open_shift = load_htv_deal_config()['prahran_shift']
    return validate_config(dict(on_target=float(on_target), greens_points=float(greens_points),
                                on_seat_types=sorted(s.upper() for s in on_seat_types),
                                greens_seats=sorted(greens_seats), labor_open_seats=sorted(labor_open_seats),
                                labor_open_shift=float(labor_open_shift)))


def validate_config(config):
    if set(config) != KEYS:
        raise ValueError('Unknown how-to-vote review configuration')
    if not (math.isfinite(config['on_target']) and .5 <= config['on_target'] <= .95):
        raise ValueError('One Nation Labor share must be between 50% and 95%')
    if not (math.isfinite(config['greens_points']) and 0 <= config['greens_points'] <= .15):
        raise ValueError('Greens open-card reduction must be between 0 and 15 points')
    if not (math.isfinite(config['labor_open_shift']) and 0 <= config['labor_open_shift'] <= 3):
        raise ValueError('Labor open-card shift must be between 0 and 3 logits')
    return config


def seat_rules(district, seat_type, config):
    """{eliminated party: rule} for one district."""
    name = str(district).strip().upper()
    rules = {}
    if str(seat_type).strip().upper() in config['on_seat_types']:
        rules['ON'] = ('ALP', 'GRN', config['on_target'], 'share')
    if name in {s.upper() for s in config['greens_seats']} and config['greens_points'] > 0:
        rules['GRN'] = ('ALP', 'LNP', config['greens_points'], 'points')
    if name in {s.upper() for s in config['labor_open_seats']}:
        rules['ALP'] = ('LNP', 'GRN', config['labor_open_shift'])
    return rules


def apply_htv_review(matrices, config):
    """Copy of the matrices with review rules merged in. Source rows unchanged; idempotent."""
    validate_config(config)
    out = {}
    for key, item in matrices.items():
        matrix = dict(item['matrix'])
        existing = dict(matrix.get('__htv_shift__', {}))
        rules = seat_rules(key, item.get('seat_type', ''), config)
        clash = {p for p in rules if p in existing and existing[p] != rules[p]}
        if clash:
            raise ValueError(f'{key}: review rule clashes with an existing rule for {sorted(clash)}')
        matrix['__htv_shift__'] = dict(existing, **rules)
        out[key] = dict(item, matrix=matrix)
    return out
