from SRC.matrix_loader import load_synth_pref_matrices

matrices = load_synth_pref_matrices()

print()
print("SYNTHETIC MATRICES LOADED")
print()

print("District count:", len(matrices))

first_key = list(matrices.keys())[0]

print()
print("First district:", first_key)
print("Seat type:", matrices[first_key]["seat_type"])
print()

for party, row in matrices[first_key]["matrix"].items():
    print()
    print(party)
    print(row)