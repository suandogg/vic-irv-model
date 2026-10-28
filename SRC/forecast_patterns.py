"""Deterministic pattern primitives for research; not connected to production.

Callers supply pattern coefficients. This module assigns no mixture probabilities,
uncertainty widths or new central values. Positive cells are not candidate flags.
"""
import numpy as np


def balance_primary_pattern(base, log_tilt, tolerance=1e-9, iterations=4000):
    """Redistribute each party spatially, preserving supplied row/column totals.

    Totals are taken from the actual production table, including any deliberate
    pre-collapse transfers, not blindly from the original user primary inputs.
    Structural zeros stay zero; a failed pattern must not be published.
    """
    base = np.asarray(base,dtype=float)
    tilt = np.asarray(log_tilt,dtype=float)
    if base.ndim!=2 or base.shape!=tilt.shape:
        raise ValueError('Pattern and primary arrays must be matching matrices')
    if not np.isfinite(base).all() or not np.isfinite(tilt).all() or (base<0).any():
        raise ValueError('Pattern inputs must be finite; primaries non-negative')
    rows,columns = base.sum(axis=1),base.sum(axis=0)
    if (rows<=0).any():
        raise ValueError('Pattern cannot balance an empty seat')
    if not np.any(tilt):
        return base.copy()
    positive = base>0
    # A row constant cancels under the constraints and prevents overflow.
    offset = np.max(np.where(positive,tilt,-np.inf),axis=1,keepdims=True)
    values = np.where(positive,base*np.exp(np.where(positive,tilt-offset,0)),0)
    if np.any((values==0)&positive):
        raise ValueError('Pattern too extreme: numerical underflow')
    for _ in range(iterations):
        sums = values.sum(axis=0)
        values *= np.divide(columns,sums,out=np.zeros_like(columns),where=sums>0)
        sums = values.sum(axis=1)
        if (sums<=0).any():
            raise ValueError('Pattern lost a seat total')
        values *= (rows/sums)[:,None]
        if np.max(np.abs(values.sum(axis=0)-columns))<=tolerance:
            return values
    raise ValueError('Pattern balancing failed to converge')


def strength_contrast(base):
    """Per-party standardised log-strength scores, with zeros excluded.

    A positive coefficient increases persistence of existing positive support.
    This changes concentration, not the underlying ranking/source of strength.
    """
    base = np.asarray(base,dtype=float)
    if base.ndim!=2 or not np.isfinite(base).all() or (base<0).any():
        raise ValueError('Invalid strength table')
    result = np.zeros_like(base)
    for j in range(base.shape[1]):
        active = base[:,j]>0
        if not active.any():
            continue
        log = np.log(base[active,j])
        sd = log.std()
        if sd>1e-12:
            result[active,j] = (log-log.mean())/sd
    return result


def centre_region_contrasts(regions, region_scores):
    """Remove constant geographic tilts using equal-seat weighting.

    This does not decorrelate geography with strength/class factors; the caller
    must still budget their overlapping variance explicitly.
    """
    values = np.asarray([region_scores[region] for region in regions],dtype=float)
    if values.ndim!=2 or not np.isfinite(values).all():
        raise ValueError('Invalid regional contrast table')
    return values-values.mean(axis=0,keepdims=True)


def tilt_preference_pattern(flows, recipient_log_tilts):
    """Change only a selected continuing-field row, not evidence source data.

    Missing/zero destinations remain zero. Deliberately cannot resolve unknown
    flows or introduce recipients: that remains the central engine's job.
    """
    if set(recipient_log_tilts)-set(flows):
        raise ValueError('Pattern names a non-continuing recipient')
    keys = list(flows)
    weights = np.asarray([flows[k] for k in keys],dtype=float)
    tilt = np.asarray([recipient_log_tilts.get(k,0.) for k in keys],dtype=float)
    if not np.isfinite(weights).all() or (weights<0).any() or not np.isfinite(tilt).all():
        raise ValueError('Invalid preference pattern')
    active = weights>0
    if not active.any():
        raise ValueError('Preference pattern has no positive flow')
    if not np.any(tilt):
        return dict(flows)
    weights[active] *= np.exp(tilt[active]-np.max(tilt[active]))
    if not np.isfinite(weights).all() or weights.sum()<=0:
        raise ValueError('Invalid transformed preference pattern')
    return dict(zip(keys,weights/weights.sum()))
