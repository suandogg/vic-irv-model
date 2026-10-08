from __future__ import annotations

from collections import Counter
from itertools import combinations, permutations
from math import exp, log

import numpy as np

from SRC.constants import PARTIES
from SRC.preference_engine import diagnose_preference_weights


EPSILON = 1e-6

# These are broad behavioural archetypes, not party memberships.  Their
# offsets are pooled across every district; only their mixture weights vary by
# primary origin and seat.  This prevents the shadow model from fitting an
# unconstrained bespoke ranking type to every seat.
VOTER_TYPE_OFFSETS = {
    "generalist": {
        "ALP": 0.0, "LNP": 0.0, "GRN": 0.0,
        "ON": 0.0, "IND": 0.0, "OTH": 0.0,
    },
    "progressive": {
        "ALP": 0.7, "LNP": -0.8, "GRN": 1.2,
        "ON": -1.2, "IND": 0.2, "OTH": -0.1,
    },
    "mainstream_conservative": {
        "ALP": -0.7, "LNP": 1.2, "GRN": -0.9,
        "ON": 0.3, "IND": 0.2, "OTH": -0.1,
    },
    "populist_right": {
        "ALP": -0.8, "LNP": 0.5, "GRN": -1.1,
        "ON": 1.4, "IND": 0.0, "OTH": 0.4,
    },
    "local_heterodox": {
        "ALP": 0.0, "LNP": 0.0, "GRN": 0.0,
        "ON": 0.1, "IND": 1.2, "OTH": 0.9,
    },
}

ORIGIN_TYPE_PRIORS = {
    "ALP": [0.30, 0.48, 0.07, 0.03, 0.12],
    "LNP": [0.30, 0.07, 0.48, 0.10, 0.05],
    "GRN": [0.30, 0.55, 0.04, 0.02, 0.09],
    "ON": [0.30, 0.03, 0.12, 0.50, 0.05],
    "IND": [0.30, 0.14, 0.11, 0.05, 0.30],
    "OTH": [0.30, 0.11, 0.11, 0.14, 0.34],
}


def _evidence_weight(basis: str) -> float:
    if basis == "ON special prior":
        return 4.0
    if basis == "federal ON evidence trial":
        return 3.0
    if basis in {"full AEC row", "partial AEC row", "posterior scenario"}:
        return 2.5
    if basis == "matrix row":
        return 2.0
    return 1.0


def fit_origin_utilities(
    origin: str,
    matrix: dict,
    seat_type: str,
    params: dict,
    posterior: dict,
    ideology: dict,
) -> dict:
    """Fit coherent Bradley-Terry utilities to all pairwise flow evidence."""
    choices = [party for party in PARTIES if party != origin]
    reference = choices[-1]
    variables = choices[:-1]
    rows, targets, weights, observations = [], [], [], []

    for party_a, party_b in combinations(choices, 2):
        diagnostic = diagnose_preference_weights(
            eliminated_party=origin,
            alive_parties=[party_a, party_b],
            matrix=matrix,
            geography_class=seat_type,
            params=params,
            posterior=posterior,
            ideology=ideology,
        )
        flows = diagnostic["final_flows"]
        probability_a = min(1.0 - EPSILON, max(EPSILON, float(flows[party_a])))
        target = log(probability_a / (1.0 - probability_a))
        row = [0.0] * len(variables)
        if party_a != reference:
            row[variables.index(party_a)] += 1.0
        if party_b != reference:
            row[variables.index(party_b)] -= 1.0
        evidence_weight = _evidence_weight(diagnostic["basis"])
        rows.append(row)
        targets.append(target)
        weights.append(evidence_weight)
        observations.append({
            "party_a": party_a,
            "party_b": party_b,
            "observed_party_a": probability_a,
            "basis": diagnostic["basis"],
            "weight": evidence_weight,
        })

    design = np.asarray(rows, dtype=float)
    response = np.asarray(targets, dtype=float)
    sqrt_weights = np.sqrt(np.asarray(weights, dtype=float))
    solution, *_ = np.linalg.lstsq(
        design * sqrt_weights[:, None],
        response * sqrt_weights,
        rcond=None,
    )
    utilities = {reference: 0.0}
    utilities.update({party: float(solution[index]) for index, party in enumerate(variables)})

    squared_errors = []
    for observation in observations:
        fitted = 1.0 / (1.0 + exp(-(
            utilities[observation["party_a"]] - utilities[observation["party_b"]]
        )))
        error = fitted - observation["observed_party_a"]
        observation["fitted_party_a"] = fitted
        observation["error"] = error
        squared_errors.append(error * error)

    return {
        "origin": origin,
        "utilities": utilities,
        "pairwise_rmse": float(np.sqrt(np.mean(squared_errors))),
        "max_pairwise_error": max(abs(row["error"]) for row in observations),
        "observations": observations,
    }


def enumerate_ranked_ballots(origin: str, utilities: dict[str, float]) -> list[dict]:
    """Enumerate a Plackett-Luce distribution of complete coherent rankings."""
    alternatives = [party for party in PARTIES if party != origin]
    cohorts = []
    for ranking_tail in permutations(alternatives):
        probability = 1.0
        remaining = list(alternatives)
        for selected in ranking_tail:
            denominator = sum(exp(utilities[party]) for party in remaining)
            probability *= exp(utilities[selected]) / denominator
            remaining.remove(selected)
        cohorts.append({
            "ranking": (origin, *ranking_tail),
            "probability": probability,
        })
    return cohorts


def _project_simplex(values: np.ndarray) -> np.ndarray:
    """Euclidean projection onto non-negative weights summing to one."""
    ordered = np.sort(values)[::-1]
    cumulative = np.cumsum(ordered)
    rho_candidates = np.nonzero(
        ordered * np.arange(1, len(values) + 1) > (cumulative - 1.0)
    )[0]
    rho = int(rho_candidates[-1])
    threshold = (cumulative[rho] - 1.0) / (rho + 1)
    return np.maximum(values - threshold, 0.0)


def fit_voter_type_mixture(
    base_fit: dict,
    type_strength: float = 1.0,
    regularization: float = 0.05,
) -> dict:
    """Fit regularised archetype weights to the available pairwise evidence.

    The archetype utility offsets are shared across seats. Only four mixture
    weights are fitted, against ten pairwise observations, with shrinkage to a
    primary-origin prior. This is deliberately more constrained than fitting
    separate utilities for every type in every seat.
    """
    type_names = list(VOTER_TYPE_OFFSETS)
    component_utilities = {}
    for type_name in type_names:
        offsets = VOTER_TYPE_OFFSETS[type_name]
        component_utilities[type_name] = {
            party: float(base_fit["utilities"][party])
            + type_strength * float(offsets[party])
            for party in base_fit["utilities"]
        }

    component_probabilities = []
    observed = []
    evidence_weights = []
    for row in base_fit["observations"]:
        party_a, party_b = row["party_a"], row["party_b"]
        component_probabilities.append([
            1.0 / (1.0 + exp(-(
                component_utilities[type_name][party_a]
                - component_utilities[type_name][party_b]
            )))
            for type_name in type_names
        ])
        observed.append(row["observed_party_a"])
        evidence_weights.append(row["weight"])

    design = np.asarray(component_probabilities, dtype=float)
    target = np.asarray(observed, dtype=float)
    evidence = np.asarray(evidence_weights, dtype=float)
    prior = np.asarray(ORIGIN_TYPE_PRIORS[base_fit["origin"]], dtype=float)
    mixture = prior.copy()

    hessian = 2.0 * design.T @ (evidence[:, None] * design)
    hessian += 2.0 * regularization * np.eye(len(type_names))
    step = 1.0 / max(float(np.linalg.eigvalsh(hessian).max()), EPSILON)
    for _ in range(2000):
        residual = design @ mixture - target
        gradient = 2.0 * design.T @ (evidence * residual)
        gradient += 2.0 * regularization * (mixture - prior)
        updated = _project_simplex(mixture - step * gradient)
        if float(np.max(np.abs(updated - mixture))) < 1e-12:
            mixture = updated
            break
        mixture = updated

    fitted = design @ mixture
    errors = fitted - target
    return {
        "type_names": type_names,
        "weights": {
            name: float(mixture[index]) for index, name in enumerate(type_names)
        },
        "component_utilities": component_utilities,
        "pairwise_rmse": float(np.sqrt(np.mean(errors ** 2))),
        "max_pairwise_error": float(np.max(np.abs(errors))),
        "type_strength": type_strength,
        "regularization": regularization,
    }


def build_latent_ballots(
    district_votes: dict[str, float],
    matrix: dict,
    seat_type: str,
    params: dict,
    posterior: dict,
    ideology: dict,
    mixture: bool = False,
    type_strength: float = 1.0,
    regularization: float = 0.05,
) -> tuple[list[dict], list[dict]]:
    ballots, fits = [], []
    for origin in PARTIES:
        primary_vote = float(district_votes.get(origin, 0.0) or 0.0)
        if primary_vote <= 0:
            continue
        fit = fit_origin_utilities(
            origin, matrix, seat_type, params, posterior, ideology
        )
        if mixture:
            mixture_fit = fit_voter_type_mixture(
                fit,
                type_strength=type_strength,
                regularization=regularization,
            )
            fit["single_pairwise_rmse"] = fit["pairwise_rmse"]
            fit["single_max_pairwise_error"] = fit["max_pairwise_error"]
            fit["pairwise_rmse"] = mixture_fit["pairwise_rmse"]
            fit["max_pairwise_error"] = mixture_fit["max_pairwise_error"]
            fit["mixture_weights"] = mixture_fit["weights"]
            for type_name, type_weight in mixture_fit["weights"].items():
                if type_weight <= 0:
                    continue
                utilities = mixture_fit["component_utilities"][type_name]
                for cohort in enumerate_ranked_ballots(origin, utilities):
                    ballots.append({
                        "origin": origin,
                        "voter_type": type_name,
                        "ranking": cohort["ranking"],
                        "votes": primary_vote * type_weight * cohort["probability"],
                    })
        else:
            for cohort in enumerate_ranked_ballots(origin, fit["utilities"]):
                ballots.append({
                    "origin": origin,
                    "voter_type": "single",
                    "ranking": cohort["ranking"],
                    "votes": primary_vote * cohort["probability"],
                })
        fits.append(fit)
    return ballots, fits


def _count_ballots(ballots: list[dict], alive: list[str]) -> dict[str, float]:
    totals = {party: 0.0 for party in PARTIES}
    alive_set = set(alive)
    for ballot in ballots:
        recipient = next(party for party in ballot["ranking"] if party in alive_set)
        totals[recipient] += ballot["votes"]
    return totals


def count_latent_irv(
    ballots: list[dict],
    forced_pair: tuple[str, str] | None = None,
) -> dict:
    primary_totals = Counter()
    for ballot in ballots:
        primary_totals[ballot["origin"]] += ballot["votes"]
    alive = [party for party in PARTIES if primary_totals[party] > 0]
    if forced_pair:
        for party in forced_pair:
            if party not in alive:
                alive.append(party)
    elimination_order = []
    votes = _count_ballots(ballots, alive)
    while len(alive) > 2:
        removable = [
            party for party in alive
            if forced_pair is None or party not in forced_pair
        ]
        if not removable:
            break
        eliminated = min(removable, key=lambda party: (votes[party], PARTIES.index(party)))
        elimination_order.append(eliminated)
        alive.remove(eliminated)
        votes = _count_ballots(ballots, alive)

    final_two = sorted(alive, key=lambda party: votes[party], reverse=True)
    total = sum(votes[party] for party in final_two)
    return {
        "winner": final_two[0],
        "runner_up": final_two[1],
        "winner_pct": votes[final_two[0]] / total if total else 0.0,
        "runner_up_pct": votes[final_two[1]] / total if total else 0.0,
        "elimination_order": ">".join(elimination_order),
        "final_votes": votes,
    }


def run_latent_ranking_all(
    primary_votes_df,
    matrices,
    params,
    posterior,
    ideology,
    mixture: bool = False,
    type_strength: float = 1.0,
    regularization: float = 0.05,
):
    """Run the coherent-ranking engine as a separately callable shadow model."""
    results, fit_rows = [], []
    for district, group in primary_votes_df.groupby("district"):
        first_row = group.iloc[0]
        key = str(district).strip().upper()
        matrix = matrices[key]["matrix"]
        district_votes = {
            row["party"]: row["primary_vote"] for _, row in group.iterrows()
        }
        ballots, fits = build_latent_ballots(
            district_votes,
            matrix,
            first_row["seat_type"],
            params,
            posterior,
            ideology,
            mixture=mixture,
            type_strength=type_strength,
            regularization=regularization,
        )
        actual = count_latent_irv(ballots)
        forced_alp_lnp = count_latent_irv(ballots, ("ALP", "LNP"))
        forced_alp_on = count_latent_irv(ballots, ("ALP", "ON"))
        results.append({
            "district": district,
            "region": first_row["region"],
            "held_by": first_row["held_by"],
            "winner": actual["winner"],
            "runner_up": actual["runner_up"],
            "winner_pct": actual["winner_pct"],
            "runner_up_pct": actual["runner_up_pct"],
            "margin": actual["winner_pct"] - 0.5,
            "matchup": f'{actual["winner"]}-{actual["runner_up"]}',
            "elimination_order": actual["elimination_order"],
            "ALP_2PP": forced_alp_lnp["final_votes"]["ALP"],
            "LNP_2PP": forced_alp_lnp["final_votes"]["LNP"],
            "ALP_ON_2CP": forced_alp_on["final_votes"]["ALP"],
            "ON_ALP_2CP": forced_alp_on["final_votes"]["ON"],
        })
        # Shares are fractions because district primary votes sum to one.
        total_alp_lnp = results[-1]["ALP_2PP"] + results[-1]["LNP_2PP"]
        total_alp_on = results[-1]["ALP_ON_2CP"] + results[-1]["ON_ALP_2CP"]
        results[-1]["ALP_2PP"] /= total_alp_lnp
        results[-1]["LNP_2PP"] /= total_alp_lnp
        results[-1]["ALP_ON_2CP"] /= total_alp_on
        results[-1]["ON_ALP_2CP"] /= total_alp_on
        for fit in fits:
            fit_rows.append({
                "district": district,
                "origin": fit["origin"],
                "pairwise_rmse": fit["pairwise_rmse"],
                "max_pairwise_error": fit["max_pairwise_error"],
                "basis_counts": dict(Counter(
                    row["basis"] for row in fit["observations"]
                )),
                "mixture_weights": fit.get("mixture_weights"),
                "single_pairwise_rmse": fit.get("single_pairwise_rmse"),
            })
    return results, fit_rows
