import pandas as pd

from SRC.upper_house_loader import (
    UPPER_PARTIES,
    load_upper_region_baseline,
    load_upper_pref_params,
    load_upper_party_relationships,
    load_upper_incumbents,
)

from SRC.upper_house import (
    derive_upper_house_projection,
    run_upper_house_all_regions,
)


# 2022 lower-house statewide vote
lower_house_targets = {
    "ALP": 33.01,
    "LNP": 29.44,
    "GRN": 10.32,
    "ON": 2.04,
}


region_baseline = load_upper_region_baseline()
params = load_upper_pref_params()
relationships = load_upper_party_relationships()
incumbents = load_upper_incumbents()


projection = derive_upper_house_projection(
    lower_house_targets=lower_house_targets,
    region_baseline=region_baseline,
    params=params,
)

print("\nSTATEWIDE TARGETS\n")
print(projection["statewide_targets"])

print("\nREGIONAL TARGETS\n")
print(projection["region_targets"])


model_results = run_upper_house_all_regions(
    region_targets=projection["region_targets"],
    relationships=relationships,
    params=params,
)

print("\nMODEL REGIONAL SEAT RESULTS\n")
print(model_results)


actual_results = (
    incumbents
    .pivot_table(
        index="region",
        columns="party",
        values="seats",
        aggfunc="sum",
        fill_value=0,
    )
    .reset_index()
)

for party in UPPER_PARTIES:
    if party not in actual_results.columns:
        actual_results[party] = 0

actual_results = actual_results[
    ["region"] + UPPER_PARTIES
]

print("\nACTUAL 2022 SEAT RESULTS\n")
print(actual_results)


comparison = model_results.merge(
    actual_results,
    on="region",
    how="outer",
    suffixes=("_model", "_actual"),
).fillna(0)

for party in UPPER_PARTIES:
    comparison[f"{party}_diff"] = (
        comparison[f"{party}_model"]
        - comparison[f"{party}_actual"]
    )

comparison_columns = ["region"]

for party in UPPER_PARTIES:
    comparison_columns.extend([
        f"{party}_model",
        f"{party}_actual",
        f"{party}_diff",
    ])

comparison = comparison[comparison_columns]

print("\nMODEL VS ACTUAL COMPARISON\n")
print(comparison.to_string(index=False))


statewide_summary = pd.DataFrame([
    {
        "party": party,
        "model_seats": int(model_results[party].sum()),
        "actual_seats": int(actual_results[party].sum()),
        "diff": int(model_results[party].sum() - actual_results[party].sum()),
    }
    for party in UPPER_PARTIES
])

print("\nSTATEWIDE MODEL VS ACTUAL SUMMARY\n")
print(statewide_summary.to_string(index=False))


print("\nTOTAL SEATS CHECK\n")

print(
    "Model:",
    int(
        model_results[UPPER_PARTIES]
        .sum()
        .sum()
    )
)

print(
    "Actual:",
    int(
        actual_results[UPPER_PARTIES]
        .sum()
        .sum()
    )
)