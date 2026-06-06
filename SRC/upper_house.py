import pandas as pd

from SRC.upper_house_loader import UPPER_PARTIES


MAJOR_LH_PARTIES = ["ALP", "LNP", "GRN", "ON"]


def as_percent(value):
    value = float(value or 0)

    if value <= 1.5:
        return value * 100

    return value


def normalise_to_100(values):
    total = sum(values.values())

    if total <= 0:
        return {
            party: 100 / len(values)
            for party in values
        }

    return {
        party: value / total * 100
        for party, value in values.items()
    }


def statewide_baselines_from_region_baseline(region_baseline):
    out = {}

    for party in UPPER_PARTIES:
        party_df = region_baseline[
            region_baseline["party"] == party
        ]

        out[party] = {
            "uh_2022": party_df["uh_2022_vote"].mean() * 100,
            "lh_2022": party_df["lh_2022_vote"].mean() * 100,
        }

    return out


def derive_statewide_upper_targets(
    lower_house_targets,
    region_baseline,
    params,
):
    baselines = statewide_baselines_from_region_baseline(region_baseline)

    raw = {}

    for party in ["ALP", "LNP", "GRN"]:
        lh_input = as_percent(lower_house_targets.get(party, 0))

        uh_2022 = baselines[party]["uh_2022"]
        lh_2022 = baselines[party]["lh_2022"]

        index = uh_2022 / lh_2022 if lh_2022 > 0 else 1

        raw[party] = lh_input * index

    # Do not use 2022 lower-house ON as a conversion base.
    raw["ON"] = as_percent(lower_house_targets.get("ON", 0))

    used = (
        raw["ALP"]
        + raw["LNP"]
        + raw["GRN"]
        + raw["ON"]
    )

    residual = max(0, 100 - used)

    oth_l_2022 = baselines["OTH_L"]["uh_2022"]
    oth_r_2022 = baselines["OTH_R"]["uh_2022"]
    oth_total_2022 = oth_l_2022 + oth_r_2022

    base_l_weight = oth_l_2022 / oth_total_2022 if oth_total_2022 > 0 else 0.5
    base_r_weight = oth_r_2022 / oth_total_2022 if oth_total_2022 > 0 else 0.5

    on_baseline = baselines["ON"]["uh_2022"]
    on_gain = max(0, raw["ON"] - on_baseline)

    siphon_r = float(params.get("ON_SIPHON_FROM_OTHR", 0.55) or 0.55)
    siphon_l = float(params.get("ON_SIPHON_FROM_OTHL", 0.10) or 0.10)

    min_r = float(params.get("OTHR_MIN_SHARE_OF_OTH", 0.25) or 0.25)
    min_l = float(params.get("OTHL_MIN_SHARE_OF_OTH", 0.25) or 0.25)

    pressure_total = max(oth_total_2022, 1e-9)

    adjusted_r_weight = base_r_weight - ((on_gain * siphon_r) / pressure_total)
    adjusted_l_weight = base_l_weight - ((on_gain * siphon_l) / pressure_total)

    adjusted_r_weight = max(min_r, adjusted_r_weight)
    adjusted_l_weight = max(min_l, adjusted_l_weight)

    weight_total = adjusted_l_weight + adjusted_r_weight

    adjusted_l_weight = adjusted_l_weight / weight_total
    adjusted_r_weight = adjusted_r_weight / weight_total

    raw["OTH_L"] = residual * adjusted_l_weight
    raw["OTH_R"] = residual * adjusted_r_weight

    return normalise_to_100(raw)


def derive_region_upper_targets(
    statewide_upper_targets,
    region_baseline,
):
    baselines = statewide_baselines_from_region_baseline(region_baseline)

    rows = []

    for region in sorted(region_baseline["region"].unique()):

        region_rows = region_baseline[
            region_baseline["region"] == region
        ]

        raw_region = {}

        for party in UPPER_PARTIES:
            party_row = region_rows[
                region_rows["party"] == party
            ]

            if party_row.empty:
                regional_2022 = 0
            else:
                regional_2022 = float(
                    party_row.iloc[0]["uh_2022_vote"]
                ) * 100

            statewide_2022 = baselines[party]["uh_2022"]

            regional_factor = (
                regional_2022 / statewide_2022
                if statewide_2022 > 0 else 1
            )

            raw_region[party] = (
                statewide_upper_targets.get(party, 0)
                * regional_factor
            )

        normalised_region = normalise_to_100(raw_region)

        for party in UPPER_PARTIES:
            rows.append({
                "region": region,
                "party": party,
                "upper_primary_vote": normalised_region[party],
            })

    return pd.DataFrame(rows)


def derive_upper_house_projection(
    lower_house_targets,
    region_baseline,
    params,
):
    statewide_targets = derive_statewide_upper_targets(
        lower_house_targets=lower_house_targets,
        region_baseline=region_baseline,
        params=params,
    )

    region_targets = derive_region_upper_targets(
        statewide_upper_targets=statewide_targets,
        region_baseline=region_baseline,
    )

    return {
        "statewide_targets": statewide_targets,
        "region_targets": region_targets,
    }