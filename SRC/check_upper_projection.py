from SRC.upper_house_loader import (
    load_upper_region_baseline,
    load_upper_pref_params,
)

from SRC.upper_house import (
    derive_upper_house_projection,
)

# Example lower-house scenario
lower_house_targets = {
    "ALP": 30.0,
    "LNP": 27.0,
    "GRN": 11.5,
    "ON": 20.0,
}

region_baseline = load_upper_region_baseline()
params = load_upper_pref_params()

projection = derive_upper_house_projection(
    lower_house_targets=lower_house_targets,
    region_baseline=region_baseline,
    params=params,
)

print("\nSTATEWIDE TARGETS\n")
print(projection["statewide_targets"])

print("\nREGIONAL TARGETS\n")
print(projection["region_targets"].head(50))