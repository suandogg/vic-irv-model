"""Opt-in proportional scaling for the Other primary. All shares here are fractions.

Off by default: without a config every caller keeps the additive method exactly.
OTH_pvi leans are measured against Other's 2022 statewide share (12.3%). One
Nation now has its own column, so the 2026 Other target is less than half that,
and target + PVI goes below zero in low-Other seats (Ashwood, Narracan), which
then clip to exactly zero even with Other candidates on the ballot.

Proportional scaling keeps each seat's 2022 relative strength instead:
    pre = target * (base + pvi) / base
so a seat at half the 2022 statewide Other share gets half the 2026 target.
"""
import numpy as np

# VEC 2022 Assembly primaries classified OTH, statewide. It also equals the mean
# of (2022 seat OTH share - OTH_pvi) across the 88 seats, the base PVI leans from.
OTH_BASE_SHARE = .1234


def load_oth_scaling_config():
    return validate_config(dict(party='OTH', base_share=OTH_BASE_SHARE))


def validate_config(config):
    if set(config) != {'party', 'base_share'}:
        raise ValueError('Unknown Other scaling configuration')
    if config['party'] != 'OTH':
        raise ValueError('Proportional scaling is only reviewed for OTH')
    if not 0 < config['base_share'] < 1:
        raise ValueError('Other scaling base share must be a fraction')
    return config


def scaled_primary(pvi, target, config):
    """Seat component: the 2022 seat share scaled by the statewide ratio."""
    base = config['base_share']
    return target*np.maximum(base+pvi, 0)/base
