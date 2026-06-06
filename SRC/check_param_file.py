from SRC.loaders import read_csv_raw
from SRC.params_loader import load_params

raw = read_csv_raw("PARAMS.csv", header=None)

print()
print("Rows containing LNP+ON and ALP:")
print()

for i in range(len(raw)):
    row_text = " | ".join(str(x) for x in raw.iloc[i].tolist())

    if "LNP+ON" in row_text and "ALP" in row_text:
        print("ROW", i)
        print(raw.iloc[i].tolist())
        print()

params = load_params()

print()
print("Parsed key:")
print(params["on_special_scenario_priors"].get("LNP+ON|ALP|Provincial"))