"""Absorb a generic prior through absent parties using the same prior table."""
def pass_through_prior(origin, alive, priors, tolerance=1e-12, max_steps=1000):
    alive = set(alive)
    def row(party):
        values = {p: max(0.0, float(v or 0)) for p, v in priors.get(party, {}).items()
                  if p != origin and p != party}
        total = sum(values.values())
        return {p: v / total for p, v in values.items()} if total else {}
    pending = row(origin)
    absorbed = {p: 0.0 for p in alive}
    for _ in range(max_steps):
        next_pending = {}
        for party, mass in pending.items():
            if party in alive:
                absorbed[party] += mass
            else:
                destinations = row(party)
                if not destinations and mass > tolerance:
                    return None  # Unsupported path: retain labelled reference projection.
                for dest, share in destinations.items():
                    next_pending[dest] = next_pending.get(dest, 0.0) + mass * share
        if sum(next_pending.values()) <= tolerance:
            total = sum(absorbed.values())
            return {p: v / total for p, v in absorbed.items()} if total else None
        pending = next_pending
    return None  # Closed transient class: do not invent a destination.
