"""Development-only allocation within a continuing broad category."""
import math


def allocate_category_flow(amount, category_flows, candidates):
    """Candidates maps id to category/tally; return candidate-level movements.

    Category shares must already be supplied by the preference evidence/engine.
    This function supplies no new inter-category or ON preference assumptions.
    """
    if not math.isfinite(amount) or amount < 0:
        raise ValueError('Invalid parcel amount')
    if any(not math.isfinite(v) or v < 0 for v in category_flows.values()):
        raise ValueError('Invalid flow share')
    if abs(sum(category_flows.values())-1) > 1e-8:
        raise ValueError('Category flows must sum to one')
    if any(not math.isfinite(c['tally']) or c['tally'] < 0 for c in candidates.values()):
        raise ValueError('Invalid candidate tally')
    movements = {key: 0.0 for key in candidates}
    for category, share in category_flows.items():
        if share == 0:
            continue
        recipients = {key: c for key, c in candidates.items() if c['category'] == category}
        total = sum(c['tally'] for c in recipients.values())
        if not recipients or total <= 0:
            raise ValueError(f'No positive continuing tally for {category}')
        for key, c in recipients.items():
            movements[key] += amount*share*c['tally']/total
    return movements
