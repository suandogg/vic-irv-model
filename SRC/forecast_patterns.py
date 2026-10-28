"""Pattern primitives used only by opt-in forecast research trials.

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


def concentration_exponents(base,coefficients):
    """Equivalent pre-balancing power; <=0 flags flattening/rank reversal.

    Balancing and other parties can also change final rankings. This is a
    diagnostic, not an assertion of final seat ordering or a rejection rule.
    """
    base = np.asarray(base,dtype=float)
    coefficients = np.asarray(coefficients,dtype=float)
    if base.ndim!=2 or coefficients.shape!=(base.shape[1],):
        raise ValueError('Invalid concentration exponent dimensions')
    if not np.isfinite(base).all() or (base<0).any() or not np.isfinite(coefficients).all():
        raise ValueError('Invalid concentration exponent inputs')
    exponents = np.ones(base.shape[1])
    for j in range(base.shape[1]):
        active = base[:,j]>0
        if active.any():
            sd = np.log(base[active,j]).std()
            if sd>1e-12:
                exponents[j] += coefficients[j]/sd
    return exponents


def concentration_pattern(base,coefficients,form='linear'):
    """Return spatial log tilts and their initial strength powers.

    Positive alternatives preserve power 1 and the linear local derivative at
    coefficient zero, NOT the same global variance or expected power. They are
    declared research priors, not neutral transformations or seat-count caps.
    """
    base = np.asarray(base,dtype=float)
    powers = concentration_exponents(base,coefficients)
    if form=='linear':
        return strength_contrast(base)*coefficients,powers
    delta = powers-1
    if form=='positive_softplus':
        offset = np.log(np.expm1(1.))
        scale = 1/(1-np.exp(-1.))
        powers = np.logaddexp(0,offset+scale*delta)
    elif form=='positive_bounded':
        # 1+tanh(delta), evaluated stably. Bounds (0,2) are an explicit prior.
        powers = 2*np.exp(-np.logaddexp(0,-2*delta))
    else:
        raise ValueError('Unknown concentration mapping')
    powers = np.where(delta==0,1.,powers)
    if not np.isfinite(powers).all() or (powers<=0).any():
        raise ValueError('Positive concentration mapping underflow/overflow; no partial run published')
    logs = np.zeros_like(base)
    np.log(base,out=logs,where=base>0)
    return logs*(powers-1),powers


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
