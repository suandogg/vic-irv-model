from SRC.params_loader import load_params

params = load_params()

print()
print("PARAMS LOADED")
print()

print("ON vote source matrix:")
print(params["on_vote_source_matrix"])

print()
print("ON row prior:")
print(params["on_row_prior"])

print()
print("Geography adjustments:")
print(params["geography_adjustments"])

print()
print("Scalar params:")
print(params["scalar_params"])

print()
print("ON special scenario priors sample:")
for i, item in enumerate(params["on_special_scenario_priors"].items()):
    print(item)
    if i >= 5:
        break