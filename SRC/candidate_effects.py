"""Opt-in candidate continuity effects. All shares at this boundary are fractions.

The sheet's *_pp fields use percentage points. Missing assumptions are errors for
enabled rows, never implicit zeroes. Historical primary is reference data only.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from SRC.constants import PARTIES
from SRC.loaders import RAW_DIR


def enabled_rows(frame):
    if frame is None or frame.empty:
        return pd.DataFrame() if frame is None else frame.copy()
    if "enabled" not in frame:
        raise ValueError("Candidate input requires enabled column")
    values = frame.enabled.fillna("").astype(str).str.strip().str.lower()
    if not values.isin(["true", "false", "1", "0", ""]).all():
        raise ValueError("Invalid candidate enabled flag")
    return frame.loc[values.isin(["true", "1"])].copy()


def load_candidate_effects(path=None):
    path = Path(path) if path else RAW_DIR / "LOWER_CANDIDATE_EFFECTS.csv"
    return pd.read_csv(path).fillna("") if path.exists() else pd.DataFrame()


def number(row, key, minimum=0, maximum=None):
    try:
        value = float(row[key])
    except (ValueError, TypeError, KeyError):
        raise ValueError(f"{row.get('candidate_id', '')}: missing/invalid {key}") from None
    if not np.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"Invalid {key}: {value}")
    return value


def weights(row, prefix, excluded):
    vector = np.array([number(row, f"{prefix}_{p}") for p in PARTIES])
    if not np.isclose(vector.sum(), 1, atol=1e-9, rtol=0):
        raise ValueError(f"{prefix} weights must sum to 1")
    if excluded in PARTIES and vector[PARTIES.index(excluded)] != 0:
        raise ValueError(f"{prefix} weight for {excluded} must be zero")
    return vector


def validate_effects(frame, districts):
    rows = enabled_rows(frame)
    if rows.empty:
        return rows
    required = {"district", "candidate_id", "current_model_group", "previous_model_group",
                "continuity_status", "baseline_component_pp", "personal_vote_retention",
                "candidate_effect_pp", "effect_sd_pp"}
    if required - set(rows):
        raise ValueError(f"Missing candidate columns: {sorted(required - set(rows))}")
    for col in ["district", "candidate_id", "current_model_group", "previous_model_group", "continuity_status"]:
        rows[col] = rows[col].fillna("").astype(str).str.strip()
    if rows.candidate_id.eq("").any() or rows.duplicated(["district", "candidate_id"]).any():
        raise ValueError("Empty or duplicate district/candidate_id")
    for _, r in rows.iterrows():
        if r.district not in districts:
            raise ValueError(f"Unknown district {r.district}")
        if r.continuity_status not in {"new", "returning", "retired", "switched"}:
            raise ValueError("Invalid continuity_status")
        base = number(r, "baseline_component_pp", maximum=100)
        number(r, "personal_vote_retention", maximum=1)
        effect = number(r, "candidate_effect_pp", maximum=100)
        number(r, "effect_sd_pp", maximum=100)
        if r.continuity_status == "new" and (base != 0 or r.previous_model_group):
            raise ValueError("New candidate cannot have a previous baseline/group")
        if r.continuity_status != "new" and r.previous_model_group not in PARTIES:
            raise ValueError("Missing previous model group")
        if r.continuity_status == "retired":
            if r.current_model_group or effect or number(r, "effect_sd_pp"):
                raise ValueError("Retired candidate cannot have current support/effect")
        elif r.current_model_group not in PARTIES:
            raise ValueError("Missing current model group")
        if r.continuity_status == "returning" and r.previous_model_group != r.current_model_group:
            raise ValueError("Returning candidate must keep model group; use switched")
        if base * (1-number(r, "personal_vote_retention")) > 0:
            weights(r, "release", r.previous_model_group)
        if effect > 0 or number(r, "effect_sd_pp") > 0:
            weights(r, "donor", r.current_model_group)
    return rows.sort_values(["district", "candidate_id"]).reset_index(drop=True)


def _allocate(demands, donor_weights, capacity):
    """Simultaneous capacity-constrained allocation; exhausted donors drop out."""
    movements = np.zeros_like(donor_weights)
    remaining = demands.copy()
    capacity = capacity.copy()
    for _ in range(100):
        available = donor_weights * (capacity > 1e-14)
        sums = available.sum(axis=1)
        proposals = np.divide(available, sums[:, None], out=np.zeros_like(available),
                              where=sums[:, None] > 0) * remaining[:, None]
        totals = proposals.sum(axis=0)
        scale = np.minimum(1, np.divide(capacity, totals, out=np.ones_like(capacity), where=totals > 0))
        accepted = proposals * scale
        if accepted.sum() < 1e-14:
            break
        movements += accepted
        remaining = np.maximum(0, remaining - accepted.sum(axis=1))
        capacity = np.maximum(0, capacity - accepted.sum(axis=0))
    return movements


def _balance_unlocked(out, current, locked, targets):
    """Keep adjusted districts fixed; restore Main's unweighted statewide targets."""
    free = ~out.district.isin(locked)
    target = np.array([float(targets[p]) for p in PARTIES])
    if not np.isfinite(target).all() or (target < 0).any() or target.sum() <= 0:
        raise ValueError("Invalid statewide targets")
    required = len(out) * target / target.sum() - out.loc[~free, PARTIES].sum().to_numpy(float)
    if (required < -1e-10).any() or abs(required.sum()-free.sum()) > 1e-9:
        raise ValueError("Candidate allocations incompatible with statewide targets")
    required = np.maximum(0, required)
    values = out.loc[free, PARTIES].to_numpy(dtype=float, copy=True)
    if not len(values):
        if np.max(np.abs(required), initial=0) > 1e-9:
            raise ValueError("No unlocked districts for statewide balancing")
        return out
    for _ in range(10000):
        sums = values.sum(axis=0)
        if ((sums == 0) & (required > 1e-12)).any():
            raise ValueError("Structural zeros incompatible with statewide targets")
        values *= np.divide(required, sums, out=np.zeros_like(required), where=sums > 0)
        row_totals = values.sum(axis=1)
        if (row_totals == 0).any():
            raise ValueError("Statewide balancing leaves an empty district")
        values /= row_totals[:, None]
        if np.max(np.abs(values.sum(axis=0)-required)) < 1e-10:
            out.loc[free, PARTIES] = values
            return out
    raise ValueError("Candidate statewide balancing did not converge")


def apply_candidate_effects(current, effects, targets, seat_adjustments=None, rng=None):
    """Apply after existing Main primary stages; keep active districts fixed in raking.

    Deterministic by default. With an explicit numpy Generator, sample effects
    from a normal clipped to [0, 100]; report realised effects, not nominal means.
    This testing sampler does not make Main a probabilistic forecast.
    """
    if current.district.duplicated().any():
        raise ValueError("Duplicate district in primary inputs")
    rows = validate_effects(effects, set(current.district))
    if rows.empty:
        return current.copy(), pd.DataFrame()
    original = current[PARTIES].to_numpy(float)
    if not np.isfinite(original).all() or (original < 0).any() or not np.allclose(original.sum(axis=1), 1):
        raise ValueError("Invalid baseline primaries")
    for _, s in enabled_rows(seat_adjustments).iterrows():
        relevant = rows[rows.district.eq(s.district)]
        # Conservative: require an explicit decomposition before combining the
        # same group's manual/candidate adjustment with named candidate effects.
        if s.party in set(relevant.current_model_group) | set(relevant.previous_model_group):
            for col in ["candidate_strength_pp", "manual_adjustment_pp"]:
                value = s.get(col, 0)
                if pd.notna(value) and str(value).strip() and float(value) != 0:
                    raise ValueError(f"Overlapping {col} in {s.district}/{s.party}")
    out = current.copy()
    diagnostics = []
    for district, group in rows.groupby("district", sort=True):
        index = out.index[out.district.eq(district)][0]
        votes = out.loc[index, PARTIES].to_numpy(dtype=float, copy=True)
        removals = np.zeros(len(PARTIES))
        embedded = np.zeros(len(PARTIES))
        releases = np.zeros(len(PARTIES))
        records = []
        for _, r in group.iterrows():
            component = number(r, "baseline_component_pp") / 100
            removed = component * (1-number(r, "personal_vote_retention"))
            if r.previous_model_group in PARTIES:
                j = PARTIES.index(r.previous_model_group)
                embedded[j] += component
                removals[j] += removed
            if removed:
                releases += removed * weights(r, "release", r.previous_model_group)
            records.append(dict(district=district, candidate_id=r.candidate_id,
                                removed_pp=removed*100, requested_effect_pp=number(r,"candidate_effect_pp"),
                                current_model_group=r.current_model_group))
        if (embedded > votes + 1e-10).any():
            raise ValueError(f"Overlapping/excess baseline components in {district}")
        votes += releases-removals
        demands, donor_rows = [], []
        for _, r in group.iterrows():
            effect = number(r, "candidate_effect_pp")
            if rng is not None and number(r, "effect_sd_pp"):
                effect = float(np.clip(rng.normal(effect, number(r,"effect_sd_pp")), 0, 100))
            demands.append(effect/100)
            donor_rows.append(weights(r,"donor",r.current_model_group) if effect else np.zeros(len(PARTIES)))
        movements = _allocate(np.array(demands), np.array(donor_rows), votes)
        votes -= movements.sum(axis=0)
        for k, (_, r) in enumerate(group.iterrows()):
            realised = movements[k].sum()
            if realised:
                votes[PARTIES.index(r.current_model_group)] += realised
            records[k].update(sampled_effect_pp=demands[k]*100, realised_effect_pp=realised*100,
                              unfunded_effect_pp=(demands[k]-realised)*100)
        out.loc[index, PARTIES] = votes
        diagnostics.extend(records)
    out = _balance_unlocked(out, current, set(rows.district), targets)
    return out, pd.DataFrame(diagnostics)
