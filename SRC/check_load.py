from SRC.loaders import load_seat_helper
from SRC.transform import build_primary_vote_table

from SRC.params_loader import load_params
from SRC.matrix_loader import load_synth_pref_matrices

from SRC.posterior_loader import load_posterior_scenarios
from SRC.ideology_loader import load_ideology_prior

from SRC.irv import run_irv_all

seat_helper = load_seat_helper()

primary_votes = build_primary_vote_table(seat_helper)

params = load_params()

matrices = load_synth_pref_matrices()

posterior = load_posterior_scenarios()

ideology = load_ideology_prior()

results = run_irv_all(
    primary_votes_df=primary_votes,
    matrices=matrices,
    params=params,
    posterior=posterior,
    ideology=ideology
)

import pandas as pd

results_df = pd.DataFrame(results)

print()
print("IRV RESULTS USING FULL PRIOR STACK")
print()

print(results_df.head(20))

print()
print("Rows:", len(results_df))

print()
print("Seat count by winner:")
print(results_df["winner"].value_counts())