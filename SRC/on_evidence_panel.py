"""Read-only, current-count parcel audit; weights are not confidence probabilities."""
from SRC.irv import initialise_parcels, parcel_totals, distribute_parcel_holder
from SRC.preference_engine import diagnose_preference_weights, alive_key

def current_on_evidence_rows(votes, matrix, seat_type, params, posterior, ideology):
    parcels = initialise_parcels(votes)
    alive = [party for party, value in parcel_totals(parcels).items() if value > 0]
    rows = []
    number = 0
    while len(alive) > 2:
        totals = parcel_totals(parcels)
        holder = min(alive, key=lambda party: totals[party])
        alive.remove(holder)
        number += 1
        diag, _, origins = distribute_parcel_holder(parcels, holder, alive, matrix,
            seat_type, params, posterior, ideology)
        for origin in origins:
            donor = origin['origin']
            if donor != 'ON' and 'ON' not in alive:
                continue
            locked = diag['basis'] == 'ON special prior'
            own = diag if donor == holder or locked else diagnose_preference_weights(
                donor, alive, matrix, seat_type, params, posterior, ideology)
            key = f'{holder if locked else donor}|{alive_key(alive)}'
            record = posterior.get(key, {})
            applied = own.get('trial_reliability', 0)
            rows.append({
                'Round': number, 'Eliminated holder': holder, 'Primary origin': donor,
                'Field': key, 'Rule used': own['basis'],
                'Parcel size (% of seat vote)': 100*origin['votes'],
                'Federal evidence seats': record.get('__evidence_seats__') if applied else None,
                'Federal blend weight (%)': 100*applied,
                'Interpretation': 'Federal blend; remaining weight uses model baseline' if applied else
                    'Locked special prior' if locked else 'No exact federal blend applied',
            })
    return rows
