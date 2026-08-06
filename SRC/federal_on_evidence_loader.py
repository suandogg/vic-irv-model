from pathlib import Path

import pandas as pd


DEVELOPMENT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data" / "development" / "FEDERAL_VIC_ON_SCENARIOS.csv"
)
RAW_PATH = (
    Path(__file__).resolve().parents[1]
    / "data" / "raw" / "FEDERAL_VIC_ON_SCENARIOS.csv"
)
CONFIG_PATH = (
    Path(__file__).resolve().parents[1]
    / "data" / "raw" / "LOWER_ON_PREF_CONFIG.csv"
)


def _bool(value) -> bool:
    return str(value).strip().upper() in {"TRUE", "YES", "1", "ON"}


def load_federal_on_config(path: Path = CONFIG_PATH) -> dict:
    raw = pd.read_csv(path)
    values = {
        str(row["Parameter"]).strip().upper(): row["Value"]
        for _, row in raw.iterrows()
    }
    return {
        "enabled": _bool(values.get("ENABLED", False)),
        "remove_on_siphon": _bool(values.get("REMOVE_ON_SIPHON", True)),
        "minimum_seats": int(float(values.get("MINIMUM_SEATS", 2))),
        "prior_equivalent_seats": float(values.get("PRIOR_EQUIVALENT_SEATS", 20)),
        "variance_penalty": float(values.get("VARIANCE_PENALTY", 10)),
        "maximum_evidence_weight": float(values.get("MAXIMUM_EVIDENCE_WEIGHT", 0.5)),
        "source_state": str(values.get("SOURCE_STATE", "VIC")).strip().upper(),
        "pooling_method": str(values.get("POOLING_METHOD", "EQUAL_SEAT")).strip().upper(),
    }


def load_federal_on_evidence(path: Path | None = None) -> dict:
    """Load pooled Victorian-federal ON evidence."""
    if path is None:
        path = RAW_PATH if RAW_PATH.exists() else DEVELOPMENT_PATH
    raw = pd.read_csv(path)
    required = {
        "Eliminated", "AliveSet", "Recipient", "EqualSeatShare", "Seats",
        "ScenarioTotal", "BetweenSeatVariance",
    }
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise ValueError(f"Federal ON evidence missing columns: {missing}")

    scenarios: dict[str, dict] = {}
    for (eliminated, alive), group in raw.groupby(["Eliminated", "AliveSet"]):
        key = f"{str(eliminated).upper()}|{'+'.join(sorted(str(alive).upper().split('+')))}"
        shares = {
            str(row["Recipient"]).upper(): float(row["EqualSeatShare"])
            for _, row in group.iterrows()
        }
        total = sum(shares.values())
        if total <= 0:
            continue
        scenarios[key] = {
            "shares": {party: value / total for party, value in shares.items()},
            "seats": int(group["Seats"].max()),
            "scenario_total": float(group["ScenarioTotal"].max()),
            "between_seat_variance": {
                str(row["Recipient"]).upper(): float(row["BetweenSeatVariance"])
                for _, row in group.iterrows()
            },
            "source": "FEDERAL_2025_VIC_STATEWIDE_POOL",
            "development_only": True,
        }
    return scenarios


def conservative_reliability(scenario: dict, config: dict | None = None) -> float:
    """Conservative evidence weight using seats and observed heterogeneity.

    Twenty prior-equivalent seats keep small samples strongly shrunk.  Mean
    recipient variance supplies an additional heterogeneity penalty.  The
    evidence can never receive more than 50% weight in this trial.
    """
    config = config or load_federal_on_config()
    seats = int(scenario["seats"])
    if seats < config["minimum_seats"]:
        return 0.0
    variances = list(scenario["between_seat_variance"].values())
    mean_variance = sum(variances) / len(variances) if variances else 0.0
    sample_weight = seats / (seats + config["prior_equivalent_seats"])
    heterogeneity_weight = 1.0 / (
        1.0 + config["variance_penalty"] * mean_variance
    )
    return min(config["maximum_evidence_weight"], sample_weight * heterogeneity_weight)


def add_conservative_trial_evidence(
    posterior: dict,
    evidence: dict,
    remove_on_siphon: bool = False,
    config: dict | None = None,
) -> dict:
    """Return a posterior copy with opt-in experimental scenario records."""
    out = dict(posterior)
    for key, scenario in evidence.items():
        reliability = conservative_reliability(scenario, config=config)
        if reliability <= 0:
            continue
        out[key] = {
            **scenario["shares"],
            "__federal_on_trial__": True,
            "__reliability__": reliability,
            "__evidence_seats__": scenario["seats"],
            "__evidence_source__": scenario["source"],
            "__remove_on_siphon__": bool(remove_on_siphon),
        }
    return out


def apply_production_federal_on_evidence(posterior: dict) -> dict:
    """Apply the Sheet-controlled production configuration when enabled."""
    config = load_federal_on_config()
    if not config["enabled"]:
        return posterior
    if config["source_state"] != "VIC":
        raise ValueError("Federal ON evidence SOURCE_STATE must remain VIC")
    if config["pooling_method"] != "EQUAL_SEAT":
        raise ValueError("Only EQUAL_SEAT federal ON evidence pooling is supported")
    return add_conservative_trial_evidence(
        posterior,
        load_federal_on_evidence(),
        remove_on_siphon=config["remove_on_siphon"],
        config=config,
    )
