from SRC.loaders import load_seat_helper
from SRC.transform import build_primary_vote_table

from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params

from SRC.posterior_loader import load_posterior_scenarios
from SRC.ideology_loader import load_ideology_prior

from SRC.irv import run_irv_all


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "outputs"


def main():

    OUTPUT_DIR.mkdir(exist_ok=True)

    seat_helper = load_seat_helper()

    primary_votes = build_primary_vote_table(seat_helper)

    matrices = load_synth_pref_matrices()

    params = load_params()

    posterior = load_posterior_scenarios()

    ideology = load_ideology_prior()

    results = run_irv_all(
        primary_votes_df=primary_votes,
        matrices=matrices,
        params=params,
        posterior=posterior,
        ideology=ideology
    )

    results_df = pd.DataFrame(results)

    output_path = OUTPUT_DIR / "python_irv_results.csv"

    results_df.to_csv(output_path, index=False)

    print()
    print("Exported Python IRV results to:")
    print(output_path)

    print()
    print("Rows:", len(results_df))

    print()
    print("Seat count by winner:")
    print(results_df["winner"].value_counts())


if __name__ == "__main__":
    main()