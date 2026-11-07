"""Opt-in taper for Labor's low-baseline seats. All shares here are fractions.

Off by default: without a config every caller keeps the additive method exactly.
The swing taper replaces target + PVI, which clips at zero in the lowest seats.
The error taper scales simulated lean error, which is otherwise the same number
of points in a 6% seat as in a 40% seat. Neither is a floor.

K was chosen from the 2002-2022 Victorian comparison in the 7 November review,
not fitted to a seat result. Seats at or above K keep the full additive swing.
"""
import numpy as np

# 75/25 blend of Labor's 2022 and 2018 statewide primaries: the base PVI leans from.
ALP_BASE_SHARE = .75*.366599+.25*.428645
DEFAULT_K = .30


def load_taper_config(k=DEFAULT_K):
    return validate_config(dict(party='ALP', base_share=ALP_BASE_SHARE, k=float(k)))


def validate_config(config):
    if set(config) != {'party', 'base_share', 'k'}:
        raise ValueError('Unknown low-baseline taper configuration')
    if config['party'] != 'ALP':
        raise ValueError('The low-baseline taper is only reviewed for ALP')
    if not 0 < config['base_share'] < 1 or not 0 < config['k'] <= 1:
        raise ValueError('Low-baseline taper shares must be fractions')
    return config


def tapered_primary(pvi, target, config):
    """Seat component for one party: the swing shrinks as the starting share falls."""
    base = config['base_share']+pvi
    swing = target-config['base_share']
    return base+swing*np.minimum(1, np.maximum(base, 0)/config['k'])


def error_scale(shares, config):
    """Multiplier on lean error for the taper party's seat shares."""
    return np.minimum(1, shares/config['k'])
