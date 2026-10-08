import sys
import time
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "SRC"
sys.path.append(str(SRC_DIR))

import pandas as pd
import streamlit as st

try:
    import resource
except ImportError:
    resource = None

from SRC.transform import build_primary_vote_table
from SRC.legacy_primary_loader import load_legacy_primary_inputs
from SRC.loaders import load_seat_held_metadata, apply_seat_held_metadata
from SRC.display_metrics import held_party_2cp_swing
from SRC.legacy_primary_model import (
    apply_seat_primary_adjustments,
    apply_on_primary_donor_geography,
    build_corrected_primary_table,
    deplete_on_primary_source_matrix,
)
from SRC.seat_adjustments_loader import load_lower_seat_adjustments
from SRC.poll_scenarios_loader import load_poll_scenarios
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios
from SRC.ideology_loader import load_ideology_prior
from SRC.federal_on_evidence_loader import apply_production_federal_on_evidence
from SRC.lnp_precollapse_loader import apply_lnp_precollapse
from SRC.baseline_loader import load_baseline_2cp
from SRC.baseline_region_loader import load_baseline_region_summary
from SRC.live_sheet_sync import sync_inputs_from_google_sheet
from SRC.turnout_loader import (
    attach_turnout_weights,
    load_lower_turnout_weights,
    turnout_weighted_share,
)
from SRC.upper_house_named_loader import load_upper_named_inputs
from SRC.upper_house_forecast import run_upper_house_forecast
from SRC.irv import (
    run_irv_all,
    trace_irv_for_district,
    trace_preference_diagnostics_for_district,
)


PARTIES = ["ALP", "LNP", "GRN", "ON", "IND", "OTH"]

REGION_ORDER = [
    "North-Eastern Metro",
    "Northern Metro",
    "Western Metro",
    "South-Eastern Metro",
    "Eastern Victoria",
    "Northern Victoria",
    "Western Victoria",
    "Southern Metro",
]

PARTY_LABELS = {
    "ALP": "Australian Labor Party - Victorian Branch",
    "LNP": "Liberal-National Coalition",
    "GRN": "Australian Greens Victoria",
    "ON": "One Nation",
    "IND": "Independents",
    "OTH": "Other",
}

PARTY_COLOURS = {
    "ALP": {"bg": "#ff0000", "text": "white"},
    "LNP": {"bg": "#4285f4", "text": "white"},
    "GRN": {"bg": "#34a853", "text": "white"},
    "ON": {"bg": "#ff6d01", "text": "white"},
    "IND": {"bg": "#46bdc6", "text": "white"},
    "OTH": {"bg": "#9900ff", "text": "white"},
}

DEFAULT_STATEWIDE = {
    "ALP": 36.66,
    "LNP": 34.48,
    "GRN": 11.50,
    "ON": 0.28,
    "IND": 5.55,
    "OTH": 11.53,
}

BASELINE_2022 = {
    "ALP": 36.66,
    "LNP": 34.48,
    "GRN": 11.50,
    "ON": 0.28,
    "IND": 5.55,
    "OTH": 11.53,
}

BASELINE_2PP_2022 = {
    "ALP": 55.00,
    "LNP": 45.00,
}

UPPER_BASELINE_SEATS_2022 = {
    "ALP": 15,
    "LNP": 14,
    "GRN": 4,
    "ON": 1,
    "AJP": 1,
    "DLP": 1,
    "LCV": 2,
    "LDP": 1,
    "SFF": 1,
}

INPUT_KEY_PREFIX = "statewide_primary_input_v1003"


APP_START_TIME = time.perf_counter()


def log_checkpoint(label):
    elapsed = time.perf_counter() - APP_START_TIME
    memory = ""

    if resource is not None:
        # Linux reports kilobytes; macOS reports bytes. The Cloud logs are Linux.
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory = f" rss_kb={rss}"

    print(
        f"[IRV_CHECKPOINT] {elapsed:.3f}s {label}{memory}",
        flush=True,
    )


log_checkpoint("app import complete")


def party_cell_style(value):
    party = str(value).split()[0]

    if party not in PARTY_COLOURS:
        for code, label in PARTY_LABELS.items():
            if value == label:
                party = code
                break

    if party not in PARTY_COLOURS:
        return ""

    colours = PARTY_COLOURS[party]

    return (
        f"background-color: {colours['bg']}; "
        f"color: {colours['text']}; "
        "font-weight: bold;"
    )


def placement_cell_style(value):
    party = str(value).strip()

    if party not in PARTY_COLOURS:
        return ""

    colours = PARTY_COLOURS[party]

    return (
        f"background-color: {colours['bg']}; "
        "color: transparent;"
    )


def blackout_cell(value):
    return (
        "background-color: black; "
        "color: black;"
    )


def elimination_position(row, position):
    order = str(row.get("elimination_order", "")).split(">")
    order = [p for p in order if p]

    mapping = {
        "6th": 0,
        "5th": 1,
        "4th": 2,
        "3rd": 3,
    }

    idx = mapping[position]
    return order[idx] if len(order) > idx else ""


def clean_baseline_value(value):
    if pd.isna(value):
        return None

    value = float(value)

    if value > 1.5:
        value = value / 100

    return value


def render_result_table(df):
    log_checkpoint(f"render_result_table start rows={len(df)} cols={len(df.columns)}")

    styled_df = (
        df.style
        .map(party_cell_style, subset=["held_by", "winner", "Result"])
        .map(placement_cell_style, subset=["2nd", "3rd", "4th", "5th", "6th"])
    )

    log_checkpoint("render_result_table styled")

    st.dataframe(
        styled_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Winner 2CP %": st.column_config.NumberColumn(format="%.2f%%"),
            "Runner-up 2CP %": st.column_config.NumberColumn(format="%.2f%%"),
            "2CP Swing %": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

    log_checkpoint("render_result_table complete")


def get_baselines_for_view(selected_view, baseline_regions):
    if selected_view == "Statewide":
        return BASELINE_2022, BASELINE_2PP_2022

    row = baseline_regions[
        baseline_regions["region"] == selected_view
    ].iloc[0]

    primary_baseline = {
        party: (clean_baseline_value(row.get(f"{party.lower()}_primary", 0)) or 0) * 100
        for party in PARTIES
    }

    two_pp_baseline = {
        "ALP": (clean_baseline_value(row.get("alp_2pp", 0)) or 0) * 100,
        "LNP": (clean_baseline_value(row.get("lnp_2pp", 0)) or 0) * 100,
    }

    return primary_baseline, two_pp_baseline


@st.cache_data(show_spinner="Syncing Google Sheet inputs and loading model data...")
def load_static_inputs():
    log_checkpoint("load_static_inputs start")
    sync_status = sync_inputs_from_google_sheet(st.secrets)
    log_checkpoint(
        "sheet sync "
        f"synced={sync_status.get('synced', 0)} "
        f"errors={len(sync_status.get('errors', []))}"
    )
    primary_inputs = load_legacy_primary_inputs()
    primary_inputs = apply_seat_held_metadata(
        primary_inputs,
        load_seat_held_metadata(),
    )
    log_checkpoint(f"loaded primary_inputs rows={len(primary_inputs)}")
    matrices = load_synth_pref_matrices()
    log_checkpoint(f"loaded matrices count={len(matrices)}")
    params = load_params()
    log_checkpoint(
        "loaded params "
        f"scalars={len(params.get('scalar_params', {}))} "
        f"specials={len(params.get('on_special_scenario_priors', {}))}"
    )
    posterior = load_posterior_scenarios()
    posterior = apply_production_federal_on_evidence(posterior)
    log_checkpoint(f"loaded posterior keys={len(posterior)}")
    ideology = load_ideology_prior()
    log_checkpoint(f"loaded ideology keys={len(ideology)}")
    baseline_2cp = load_baseline_2cp()
    log_checkpoint(f"loaded baseline_2cp rows={len(baseline_2cp)}")
    baseline_regions = load_baseline_region_summary()
    log_checkpoint(f"loaded baseline_regions rows={len(baseline_regions)}")
    turnout_weights = load_lower_turnout_weights()
    log_checkpoint(f"loaded turnout_weights rows={len(turnout_weights)}")

    seat_adjustments = load_lower_seat_adjustments()
    log_checkpoint(f"loaded seat_adjustments rows={len(seat_adjustments)}")
    poll_scenarios = load_poll_scenarios()
    log_checkpoint(f"loaded poll_scenarios rows={len(poll_scenarios)}")
    upper_inputs = load_upper_named_inputs()
    log_checkpoint("loaded named upper-house inputs")

    return (
        primary_inputs,
        matrices,
        params,
        posterior,
        ideology,
        baseline_2cp,
        baseline_regions,
        turnout_weights,
        seat_adjustments,
        poll_scenarios,
        upper_inputs,
        sync_status,
    )


def params_for_scenario(params, targets):
    scenario_params = dict(params)
    scenario_params["scalar_params"] = dict(params.get("scalar_params", {}))
    target_total = sum(max(0.0, float(value)) for value in targets.values())
    scenario_params["scalar_params"]["SCENARIO_ON_PRIMARY"] = (
        max(0.0, float(targets.get("ON", 0.0))) / target_total * 100
        if target_total > 0 else 0.0
    )
    return scenario_params


def run_model(
    primary_inputs, matrices, params, posterior, ideology, targets,
    seat_adjustments=None, turnout_weights=None,
):
    log_checkpoint(f"run_model start targets={targets}")
    scenario_params = params_for_scenario(params, targets)
    on_alpha = float(
        scenario_params.get("scalar_params", {}).get("ON alpha", 0.6) or 0.6
    )
    grn_pvi_persistence = float(
        scenario_params.get("scalar_params", {}).get(
            "GRN_PVI_PERSISTENCE", 1.0
        ) or 1.0
    )
    adjusted = build_corrected_primary_table(
        primary_inputs=primary_inputs,
        targets=targets,
        on_alpha=on_alpha,
        pvi_strengths={"GRN": grn_pvi_persistence},
    )
    donor_strength = float(
        scenario_params.get("scalar_params", {}).get(
            "ON_PRIMARY_DONOR_STRENGTH", 0.0
        ) or 0.0
    )
    source_matrix = scenario_params.get("on_vote_source_matrix", {})
    depletion_strength = float(
        scenario_params.get("scalar_params", {}).get(
            "ON_PRIMARY_OTH_DEPLETION_STRENGTH", 0.0
        ) or 0.0
    )
    if depletion_strength > 0:
        source_matrix = deplete_on_primary_source_matrix(
            source_matrix,
            on_level=scenario_params["scalar_params"]["SCENARIO_ON_PRIMARY"],
            max_depletion=depletion_strength,
            start_level=float(scenario_params["scalar_params"].get(
                "ON_PRIMARY_OTH_DEPLETION_START", 10.0
            )),
            full_level=float(scenario_params["scalar_params"].get(
                "ON_PRIMARY_OTH_DEPLETION_FULL", 30.0
            )),
        )
    adjusted = apply_on_primary_donor_geography(
        primary_inputs=primary_inputs,
        current=adjusted,
        targets=targets,
        source_matrix=source_matrix,
        strength=donor_strength,
        on_alpha=on_alpha,
    )
    adjusted, seat_adjustment_diagnostics = apply_seat_primary_adjustments(
        current=adjusted,
        adjustments=seat_adjustments,
        targets=targets,
        retirement_penalty_pp=float(scenario_params["scalar_params"].get(
            "RETIRING_INCUMBENT_PENALTY_PP", 1.0
        )),
        sophomore_bonus_pp=float(scenario_params["scalar_params"].get(
            "SOPHOMORE_SURGE_BONUS_PP", 1.0
        )),
    )
    adjusted = apply_lnp_precollapse(adjusted)
    log_checkpoint("run_model adjusted primaries")

    primary_votes = build_primary_vote_table(adjusted)
    log_checkpoint(f"run_model primary_votes rows={len(primary_votes)}")

    # OTH voters who remain after ON has grown are expected to be less
    # ON-friendly. Pass the normalised scenario vote into the preference
    # engine; the adjustment itself remains controlled by PARAMS.
    results = run_irv_all(
        primary_votes_df=primary_votes,
        matrices=matrices,
        params=scenario_params,
        posterior=posterior,
        ideology=ideology,
    )
    log_checkpoint(f"run_model irv complete results={len(results)}")

    results_df = pd.DataFrame(results)
    if turnout_weights is not None:
        results_df = attach_turnout_weights(results_df, turnout_weights)
    return results_df, adjusted, seat_adjustment_diagnostics


def region_primary_shares(adjusted_seat_helper):
    totals = {
        party: adjusted_seat_helper[party].sum()
        for party in PARTIES
    }

    total = sum(totals.values())

    return {
        party: totals[party] / total * 100 if total > 0 else 0
        for party in PARTIES
    }


def build_display_df(results_df, baseline_lookup):
    display_df = results_df.copy()

    display_df["2CP Swing %"] = display_df.apply(
        lambda row: held_party_2cp_swing(row, baseline_lookup),
        axis=1
    )

    display_df["Winner 2CP %"] = (display_df["winner_pct"] * 100).round(2)
    display_df["Runner-up 2CP %"] = (display_df["runner_up_pct"] * 100).round(2)
    display_df["2CP Swing %"] = display_df["2CP Swing %"].round(2)

    display_df["Result"] = display_df.apply(
        lambda row: f'{row["winner"]} {"RETAIN" if row["winner"] == row["held_by"] else "GAIN"}',
        axis=1
    )

    display_df["2nd"] = display_df["runner_up"]

    for position in ["3rd", "4th", "5th", "6th"]:
        display_df[position] = display_df.apply(
            lambda row, pos=position: elimination_position(row, pos),
            axis=1
        )

    column_order = [
        "district",
        "region",
        "held_by",
        "winner",
        "runner_up",
        "Winner 2CP %",
        "Runner-up 2CP %",
        "2CP Swing %",
        "Result",
        "2nd",
        "3rd",
        "4th",
        "5th",
        "6th",
    ]

    return display_df[column_order], column_order


st.set_page_config(
    page_title="Victorian IRV Model",
    layout="wide"
)

st.title("Victorian IRV Election Model")

(
    primary_inputs,
    matrices,
    params,
    posterior,
    ideology,
    baseline_2cp,
    baseline_regions,
    turnout_weights,
    seat_adjustments,
    poll_scenarios,
    upper_inputs,
    sync_status,
) = load_static_inputs()

from tools.preference_review_trials import variant as preference_trial_variant
from tools.trial_posterior_reliability import seat_count_trial
trial_options = {
    "Current reference": "reference",
    "Matrix source only, retain extra transforms": "matrix_source_only",
    "Single synthetic ON fallback baseline": "single_on_baseline",
    "Keep ON source selection, remove extra transforms": "on_no_extra_transforms",
    "No generic ON siphon": "no_siphon",
    "No preference geography": "no_geography",
    "No ON-recipient geography addition": "no_on_recipient_geography",
    "No non-ON-recipient geography additions": "no_non_on_recipient_geography",
    "No preference floors or caps": "no_constraints",
    "Remove complete-row priority in ON rounds": "no_synthetic_priority",
    "Combined simplified preferences": "simplified",
    "Seat-count shrinkage: 5 prior seats": "seat_reliability_5",
    "Seat-count shrinkage: 10 prior seats": "seat_reliability_10",
    "Seat-count shrinkage: 20 prior seats": "seat_reliability_20",
}
trial_label = st.sidebar.selectbox("Preference trial", list(trial_options))
trial_method = trial_options[trial_label]
params = preference_trial_variant(params, trial_method)
if trial_method.startswith("seat_reliability_"):
    posterior = seat_count_trial(posterior, int(trial_method.rsplit("_", 1)[1]))
st.sidebar.caption("Development comparisons with frozen inputs. Trial choice affects Assembly preferences.")
if trial_method == "single_on_baseline":
    st.sidebar.caption("Matrix-direct sensitivity: replaces generic posterior/prior selection in ON-related rounds. Exact federal blending remains; special priors are locked. Not a production recommendation.")
elif trial_method == "on_no_extra_transforms":
    st.sidebar.caption("Narrow overlap test: retains existing source selection, but removes geography and siphon in ON-related rounds. Non-ON rounds remain unchanged.")
elif trial_method == "no_synthetic_priority":
    st.sidebar.caption("Broad hierarchy sensitivity: applies to all ON-related rows until provenance is established.")
elif trial_method.startswith("seat_reliability_"):
    st.sidebar.caption("Seat-count sensitivity only; between-seat variance is not available in the current scenario input.")

baseline_lookup = baseline_2cp.set_index("district")

if sync_status.get("synced", 0) > 0:
    st.sidebar.caption(sync_status.get("message", "Google Sheet inputs synced"))
elif sync_status.get("message"):
    st.sidebar.caption(f"Using committed CSV inputs ({sync_status['message']}).")
if sync_status.get("errors"):
    st.sidebar.warning(
        "Some Google Sheet tabs could not be synced; using available CSV inputs."
    )

house_view = st.sidebar.radio(
    "View",
    ["Dashboard", "Legislative Assembly", "Legislative Council"],
    horizontal=False,
)

if house_view == "Legislative Council":
    st.header("Legislative Council forecast")
    st.caption(
        "Development model using named-party regional primaries, voter-controlled "
        "preferences and candidate-level proportional counting."
    )
    upper_targets = {
        party: float(st.session_state.get(f"{INPUT_KEY_PREFIX}_{party}", DEFAULT_STATEWIDE[party]))
        for party in PARTIES
    }
    target_total = sum(upper_targets.values())
    if target_total <= 0:
        st.error("Lower-house statewide primary inputs must have a positive total.")
        st.stop()
    upper_targets = {party: value / target_total * 100 for party, value in upper_targets.items()}
    st.info(
        "This view currently derives its major-party statewide inputs from the saved "
        "Legislative Assembly scenario. Change them in the Assembly view, then return here."
    )
    with st.spinner("Running candidate-level Legislative Council count..."):
        upper_projection = run_upper_house_forecast(upper_inputs, upper_targets)

    summary = upper_projection["statewide"].copy()
    family_summary = summary.groupby("PartyFamily", as_index=False).agg(
        **{"Primary input %": ("StatewidePrimaryPct", "sum"), "Seats": ("Seats", "max")}
    ).sort_values(["Seats", "Primary input %"], ascending=False)
    st.subheader("Statewide summary")
    st.dataframe(
        family_summary,
        width="stretch",
        hide_index=True,
        column_config={"Primary input %": st.column_config.NumberColumn(format="%.2f%%")},
    )

    result = upper_projection["results"].copy()
    st.subheader("Members elected by region")
    st.dataframe(
        result[[
            "Region", "ElectedOrder", "Candidate", "GroupKey", "FinalTallyQuotas",
            "FinalSeatMarginVotes", "Reliability", "ExhaustedPct",
        ]],
        width="stretch",
        hide_index=True,
        column_config={
            "FinalTallyQuotas": st.column_config.NumberColumn("Tally when count concluded (quotas)", format="%.3f"),
            "FinalSeatMarginVotes": st.column_config.NumberColumn("Final-seat margin", format="%d"),
            "ExhaustedPct": st.column_config.NumberColumn("Exhausted %", format="%.2f%%"),
        },
    )

    st.subheader("Regional primary estimates")
    region_table = upper_projection["regions"].pivot(
        index="Region", columns="PartyKey", values="UpperPrimaryPct"
    ).reset_index()
    st.dataframe(region_table, width="stretch", hide_index=True)

    with st.expander("Upper-house reliability and evidence diagnostics", expanded=False):
        low_reliability = result[result["ElectedOrder"].eq(5)][[
            "Region", "GroupKey", "FinalSeatMarginVotes", "Reliability", "ExhaustedPct"
        ]]
        st.caption(
            "Reliability describes sensitivity of the final regional seat to modest "
            "preference or input changes; it is not a win probability."
        )
        st.dataframe(low_reliability, width="stretch", hide_index=True)
        st.dataframe(
            upper_projection["preference_diagnostics"], width="stretch", hide_index=True
        )
        st.dataframe(upper_projection["ballots"], width="stretch", hide_index=True)
    st.stop()

selected_view = st.selectbox(
    "Select region",
    ["Statewide"] + REGION_ORDER,
    index=0
)

primary_baseline, two_pp_baseline = get_baselines_for_view(
    selected_view,
    baseline_regions
)

st.subheader("Statewide Scenario Inputs")

log_checkpoint("scenario inputs start")

if not poll_scenarios.empty:
    scenario_names = poll_scenarios["scenario"].tolist()
    saved_scenario = st.selectbox(
        "Saved polling scenario",
        scenario_names,
        key="saved_lower_poll_scenario",
    )
    saved_row = poll_scenarios.loc[
        poll_scenarios["scenario"].eq(saved_scenario)
    ].iloc[0]
    if st.button("Apply saved polling scenario"):
        for party in PARTIES:
            st.session_state[f"{INPUT_KEY_PREFIX}_{party}"] = float(saved_row[party])
        st.rerun()

if st.button("Reset scenario inputs"):
    for party in PARTIES:
        st.session_state[f"{INPUT_KEY_PREFIX}_{party}"] = DEFAULT_STATEWIDE[party]
    st.rerun()

input_columns = st.columns(len(PARTIES))

targets = {}

for column, party in zip(input_columns, PARTIES):
    with column:
        targets[party] = st.number_input(
            party,
            min_value=0.0,
            max_value=100.0,
            value=DEFAULT_STATEWIDE[party],
            step=0.01,
            format="%.2f",
            key=f"{INPUT_KEY_PREFIX}_{party}",
        )

log_checkpoint(f"scenario inputs complete targets={targets}")

total_primary = sum(targets.values())

st.markdown(f"**Primary total: {total_primary:.2f}%**")

with st.expander("Five-seat preference trial comparisons", expanded=False):
    from SRC.trial_seat_panel import comparison_panel, EXPLANATIONS
    from pathlib import Path
    st.caption("Saved fixed-primary tests, not the current interactive polling inputs. Winning margin means the winner's share above 50%; forced ALP–LNP 2PP provides a consistent comparison when finalists change.")
    panel_scenario = st.selectbox("Fixed test scenario", ["ON18", "ON20", "ON24", "2022"], key="trial_panel_scenario")
    panel_variant = st.selectbox("Comparison variant", list(trial_options), key="trial_panel_variant")
    st.caption(EXPLANATIONS[trial_options[panel_variant]])
    st.caption({"ON18":"ALP 29, LNP 32, GRN 12, ON 18, IND 4.5, OTH 4.5", "ON20":"ALP 25, LNP 30, GRN 14, ON 20, IND 5.5, OTH 5.5", "ON24":"ALP 25, LNP 28, GRN 12, ON 24, IND 5.5, OTH 5.5", "2022":"Projected baseline-input sensitivity, not the actual-primary historical validation."}[panel_scenario])
    panel_results = pd.read_csv(Path(__file__).resolve().parent / "reports/preference_review_2026_10_08/seat_results.csv")
    panel = pd.DataFrame(comparison_panel(panel_results, panel_scenario, trial_options[panel_variant], matrices))
    st.dataframe(panel, hide_index=True)
    st.download_button("Download five-seat comparison", panel.to_csv(index=False), "five_seat_comparison.csv", "text/csv")

if abs(total_primary - 100) > 0.01:
    st.warning(
        "Primary votes should add to 100%. "
        "The model will normalise internally."
    )

results_df, adjusted_seat_helper, seat_adjustment_diagnostics = run_model(
    primary_inputs,
    matrices,
    params,
    posterior,
    ideology,
    targets,
    seat_adjustments,
    turnout_weights,
)

if house_view == "Dashboard":
    upper_targets = {
        party: float(targets[party]) / total_primary * 100
        for party in PARTIES
    } if total_primary > 0 else DEFAULT_STATEWIDE
    with st.spinner("Building both-chamber dashboard..."):
        upper_projection = run_upper_house_forecast(upper_inputs, upper_targets)

    assembly_seats = results_df["winner"].value_counts().to_dict()
    assembly_held = adjusted_seat_helper["held_by"].value_counts().to_dict()
    alp_seats = int(assembly_seats.get("ALP", 0))
    lnp_seats = int(assembly_seats.get("LNP", 0))
    on_seats = int(assembly_seats.get("ON", 0))
    if alp_seats >= 45:
        government_result = "Labor Majority"
    elif lnp_seats >= 45:
        government_result = "LNP Majority"
    elif lnp_seats + on_seats >= 45:
        government_result = "LNP–ON Coalition"
    else:
        government_result = "Hung Parliament"

    alp_2pp = turnout_weighted_share(results_df, "ALP_2PP") * 100
    lnp_2pp = turnout_weighted_share(results_df, "LNP_2PP") * 100
    alp_on_2cp = turnout_weighted_share(results_df, "ALP_ON_2CP") * 100
    on_alp_2cp = turnout_weighted_share(results_df, "ON_ALP_2CP") * 100

    st.header("Election dashboard")
    result_col, alp_2pp_col, lnp_2pp_col, alt_col = st.columns([1.5, 1, 1, 1.35])
    result_col.metric("Projected result", government_result)
    alp_2pp_col.metric("ALP 2PP", f"{alp_2pp:.2f}%", f"{alp_2pp - 55:.2f} pp")
    lnp_2pp_col.metric("LNP 2PP", f"{lnp_2pp:.2f}%", f"{lnp_2pp - 45:.2f} pp")
    alt_col.metric("Alternate 2CP", f"ALP {alp_on_2cp:.2f}%", f"ON {on_alp_2cp:.2f}%", delta_color="off")

    assembly_rows = []
    for party in PARTIES:
        seats = int(assembly_seats.get(party, 0))
        held = int(assembly_held.get(party, 0))
        assembly_rows.append({
            "Party": party,
            "Seats": seats,
            "Change": seats - held,
            "Currently held": held,
        })
    assembly_summary = pd.DataFrame(assembly_rows)

    upper_party_family = upper_inputs["party_inputs"].set_index("PartyKey")["PartyFamily"].to_dict()
    council_seats = {}
    for party in upper_projection["results"]["PartyKey"]:
        family = upper_party_family.get(party, party)
        council_seats[family] = council_seats.get(family, 0) + 1
    council_held = UPPER_BASELINE_SEATS_2022.copy()
    council_parties = sorted(set(council_seats) | set(council_held))
    council_summary = pd.DataFrame([
        {
            "Party": party,
            "Seats": int(council_seats.get(party, 0)),
            "Change": int(council_seats.get(party, 0) - council_held.get(party, 0)),
            "Currently held": int(council_held.get(party, 0)),
        }
        for party in council_parties
    ]).sort_values(["Seats", "Party"], ascending=[False, True])

    assembly_col, council_col = st.columns(2)
    with assembly_col:
        st.subheader("Legislative Assembly · 88 seats")
        st.caption("45 seats required for a majority")
        st.dataframe(assembly_summary, width="stretch", hide_index=True)
    with council_col:
        st.subheader("Legislative Council · 40 seats")
        st.caption("21 seats required for a chamber majority")
        st.dataframe(council_summary, width="stretch", hide_index=True)

    st.subheader("Government formation")
    formation = pd.DataFrame([
        {"Path": "Labor", "Seats": alp_seats, "Majority threshold": 45, "Status": "Majority" if alp_seats >= 45 else "Short"},
        {"Path": "LNP", "Seats": lnp_seats, "Majority threshold": 45, "Status": "Majority" if lnp_seats >= 45 else "Short"},
        {"Path": "LNP + ON", "Seats": lnp_seats + on_seats, "Majority threshold": 45, "Status": "Majority" if lnp_seats + on_seats >= 45 else "Short"},
    ])
    formation["Seats from majority"] = formation["Seats"] - formation["Majority threshold"]
    st.dataframe(formation, width="stretch", hide_index=True)

    with st.expander("Dashboard methodology", expanded=False):
        st.write(
            "Government formation is determined from the 88-seat Legislative Assembly. "
            "The result label applies this order: Labor majority, LNP majority, "
            "LNP–ON coalition majority, then hung parliament. Legislative Council seats "
            "are reported separately and do not determine who forms government."
        )
    st.stop()

with st.expander("Production diagnostics", expanded=False):
    model_primary = {
        party: float(adjusted_seat_helper[party].mean()) * 100
        for party in PARTIES
    }
    target_total = sum(max(0.0, float(value)) for value in targets.values())
    normalised_targets = {
        party: max(0.0, float(targets[party])) / target_total * 100
        if target_total > 0 else 0.0
        for party in PARTIES
    }
    reconciliation = pd.DataFrame([
        {
            "party": party,
            "normalised input %": normalised_targets[party],
            "model statewide %": model_primary[party],
            "difference pp": model_primary[party] - normalised_targets[party],
        }
        for party in PARTIES
    ])
    st.caption(
        f"Input source: {'Google Sheets' if sync_status.get('synced', 0) else 'committed CSV fallback'}; "
        f"synced tabs: {sync_status.get('synced', 0)}; "
        f"active seat adjustments: {len(seat_adjustment_diagnostics)}."
    )
    st.dataframe(
        reconciliation,
        width="stretch",
        hide_index=True,
        column_config={
            column: st.column_config.NumberColumn(format="%.4f")
            for column in ["normalised input %", "model statewide %", "difference pp"]
        },
    )
    row_sum_error = (
        adjusted_seat_helper[PARTIES].sum(axis=1) - 1
    ).abs().max()
    st.caption(
        f"Maximum seat primary row-sum error: {row_sum_error:.3e}. "
        f"Negative primary cells: {(adjusted_seat_helper[PARTIES] < 0).sum().sum()}."
    )
    if not seat_adjustment_diagnostics.empty:
        st.dataframe(
            seat_adjustment_diagnostics,
            width="stretch",
            hide_index=True,
            column_config={
                column: st.column_config.NumberColumn(format="%.2f")
                for column in [
                    "retirement_pp", "sophomore_pp", "candidate_strength_pp",
                    "manual_adjustment_pp", "requested_total_pp",
                    "pre_calibration_change_pp", "final_change_pp",
                ]
            },
        )

active_scenario_params = params_for_scenario(params, targets)

if selected_view == "Statewide":
    view_results_df = results_df.copy()
    view_seat_helper = adjusted_seat_helper.copy()
    view_title = "Statewide"
else:
    view_results_df = results_df[
        results_df["region"] == selected_view
    ].copy()

    view_seat_helper = adjusted_seat_helper[
        adjusted_seat_helper["region"] == selected_view
    ].copy()

    view_title = selected_view


st.subheader(f"{view_title} Primary Vote")

view_primary = region_primary_shares(view_seat_helper)

primary_df = pd.DataFrame([
    {
        "Party": PARTY_LABELS[party],
        "Primary Vote %": view_primary[party],
        "Swing %": view_primary[party] - primary_baseline[party],
    }
    for party in PARTIES
])

st.dataframe(
    primary_df.style.map(party_cell_style, subset=["Party"]),
    width="stretch",
    hide_index=True,
    column_config={
        "Primary Vote %": st.column_config.NumberColumn(format="%.2f%%"),
        "Swing %": st.column_config.NumberColumn(format="%.2f%%"),
    },
)


st.subheader(f"{view_title} Summary")

seat_count_map = view_results_df["winner"].value_counts().to_dict()
held_count_map = view_seat_helper["held_by"].value_counts().to_dict()

alp_2pp = turnout_weighted_share(view_results_df, "ALP_2PP") * 100
lnp_2pp = turnout_weighted_share(view_results_df, "LNP_2PP") * 100

summary_df = pd.DataFrame([
    {
        "Party": PARTY_LABELS["ALP"],
        "2PP %": alp_2pp,
        "2PP Swing %": alp_2pp - two_pp_baseline["ALP"],
        "Seats": seat_count_map.get("ALP", 0),
        "Change": seat_count_map.get("ALP", 0) - held_count_map.get("ALP", 0),
    },
    {
        "Party": PARTY_LABELS["LNP"],
        "2PP %": lnp_2pp,
        "2PP Swing %": lnp_2pp - two_pp_baseline["LNP"],
        "Seats": seat_count_map.get("LNP", 0),
        "Change": seat_count_map.get("LNP", 0) - held_count_map.get("LNP", 0),
    },
    *[
        {
            "Party": PARTY_LABELS[party],
            "2PP %": 0.0,
            "2PP Swing %": 0.0,
            "Seats": seat_count_map.get(party, 0),
            "Change": seat_count_map.get(party, 0) - held_count_map.get(party, 0),
        }
        for party in ["GRN", "ON", "IND", "OTH"]
    ],
])

summary_style = (
    summary_df.style
    .map(party_cell_style, subset=["Party"])
    .map(
        blackout_cell,
        subset=pd.IndexSlice[
            summary_df.index[2:],
            ["2PP %", "2PP Swing %"]
        ]
    )
)

st.dataframe(
    summary_style,
    width="stretch",
    hide_index=True,
    column_config={
        "2PP %": st.column_config.NumberColumn(format="%.2f%%"),
        "2PP Swing %": st.column_config.NumberColumn(format="%.2f%%"),
    },
)

with st.expander("Result sensitivity (not probabilities)", expanded=False):
    sensitivity = view_results_df[[
        "district", "held_by", "winner", "runner_up", "winner_pct", "runner_up_pct"
    ]].copy()
    sensitivity["final margin %"] = (
        (sensitivity["winner_pct"] - sensitivity["runner_up_pct"]) * 100
    )
    sensitivity["winner_pct"] = sensitivity["winner_pct"] * 100
    sensitivity["runner_up_pct"] = sensitivity["runner_up_pct"] * 100
    sensitivity["sensitivity"] = pd.cut(
        sensitivity["final margin %"],
        bins=[-float("inf"), 2, 5, 10, float("inf")],
        labels=["Very high (<2)", "High (2–5)", "Moderate (5–10)", "Lower (10+)"]
    ).astype(str)
    sensitivity = sensitivity.sort_values("final margin %")
    st.caption(
        "These bands describe sensitivity to modest input or preference-flow changes. "
        "They are not Monte Carlo win probabilities."
    )
    st.dataframe(
        sensitivity,
        width="stretch",
        hide_index=True,
        column_config={
            "winner_pct": st.column_config.NumberColumn("winner %", format="%.2f%%"),
            "runner_up_pct": st.column_config.NumberColumn("runner-up %", format="%.2f%%"),
            "final margin %": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )


st.subheader(f"{view_title} Alternate 2PP")

alp_on_2cp = turnout_weighted_share(view_results_df, "ALP_ON_2CP") * 100
on_alp_2cp = turnout_weighted_share(view_results_df, "ON_ALP_2CP") * 100

alternate_2pp_df = pd.DataFrame([
    {
        "Party": PARTY_LABELS["ALP"],
        "2CP %": alp_on_2cp,
    },
    {
        "Party": PARTY_LABELS["ON"],
        "2CP %": on_alp_2cp,
    },
])

st.dataframe(
    alternate_2pp_df.style.map(party_cell_style, subset=["Party"]),
    width="stretch",
    hide_index=True,
    column_config={
        "2CP %": st.column_config.NumberColumn(format="%.2f%%"),
    },
)


results_view = st.radio(
    "Results view",
    ["Summary", "Seat Detail"],
    horizontal=True,
)


if results_view == "Summary":

    st.subheader(f"{view_title} District Results")

    display_df, column_order = build_display_df(
        view_results_df,
        baseline_lookup
    )

    render_result_table(display_df)

    st.subheader(f"{view_title} Seats Changing Hands")

    changes_df = display_df[
        display_df["held_by"] != display_df["winner"]
    ].copy()

    changes_df = changes_df.sort_values("2CP Swing %")
    changes_df = changes_df[column_order]

    render_result_table(changes_df)

else:

    st.subheader("Seat Detail Explorer")

    detail_display, _ = build_display_df(
        view_results_df,
        baseline_lookup
    )

    primary_detail = view_seat_helper[["district"] + PARTIES].copy()

    for party in PARTIES:
        primary_detail[f"{party} Primary %"] = primary_detail[party] * 100
        primary_detail[f"{party} Swing %"] = (
            primary_detail[f"{party} Primary %"] - primary_baseline[party]
        )

    primary_detail = primary_detail.drop(columns=PARTIES)

    detail_display = detail_display.merge(
        primary_detail,
        on="district",
        how="left",
    )

    seat_detail_percent_cols = [
        col for col in detail_display.columns
        if col.endswith("Primary %")
        or col.endswith("Swing %")
        or col in ["Winner 2CP %", "Runner-up 2CP %", "2CP Swing %"]
    ]

    seat_detail_column_config = {
        col: st.column_config.NumberColumn(col, format="%.2f%%")
        for col in seat_detail_percent_cols
    }

    st.dataframe(
        detail_display.style
        .map(party_cell_style, subset=["held_by", "winner", "Result"])
        .map(placement_cell_style, subset=["2nd", "3rd", "4th", "5th", "6th"]),
        width="stretch",
        hide_index=True,
        column_config=seat_detail_column_config,
    )

    selected_seat = st.selectbox(
        "Select district to inspect IRV count",
        sorted(detail_display["district"].unique()),
    )

    selected_seat_helper = adjusted_seat_helper[
        adjusted_seat_helper["district"] == selected_seat
    ].copy()

    selected_group = build_primary_vote_table(
        selected_seat_helper
    )

    seat_row = selected_group.iloc[0]

    district_votes = {
        row["party"]: row["primary_vote"]
        for _, row in selected_group.iterrows()
    }

    matrix = matrices[
        selected_seat.upper()
    ]["matrix"]

    trace_rows = trace_irv_for_district(
        district_votes=district_votes,
        matrix=matrix,
        seat_type=seat_row["seat_type"],
        params=active_scenario_params,
        posterior=posterior,
        ideology=ideology,
    )

    trace_df = pd.DataFrame(trace_rows)

    for party in PARTIES:
        if party in trace_df.columns:
            trace_df[party] = (
                trace_df[party] * 100
            ).round(2)

        flow_col = f"{party}_flow"

        if flow_col in trace_df.columns:
            trace_df[flow_col] = (
                trace_df[flow_col] * 100
            ).round(2)

    trace_column_config = {
        party: st.column_config.NumberColumn(party, format="%.2f%%")
        for party in PARTIES
    }

    st.subheader(f"{selected_seat} IRV Count Trace")

    st.dataframe(
        trace_df,
        width="stretch",
        hide_index=True,
        column_config=trace_column_config,
    )

    show_preference_diagnostics = st.checkbox(
        "Show preference flow diagnostics",
        value=False,
    )

    if show_preference_diagnostics:
        diagnostic_rows = trace_preference_diagnostics_for_district(
            district_votes=district_votes,
            matrix=matrix,
            seat_type=seat_row["seat_type"],
            params=active_scenario_params,
            posterior=posterior,
            ideology=ideology,
        )

        diagnostics_df = pd.DataFrame(diagnostic_rows)

    if show_preference_diagnostics and not diagnostics_df.empty:
        diagnostic_round = st.selectbox(
            "Select elimination round for preference diagnostics",
            diagnostics_df["round"].unique(),
        )

        round_diagnostics = diagnostics_df[
            diagnostics_df["round"] == diagnostic_round
        ].copy()

        for party in PARTIES:
            round_diagnostics[f"{party} flow %"] = (
                round_diagnostics[party] * 100
            ).round(2)

        round_diagnostics["ON change pp"] = (
            round_diagnostics["ON flow %"].diff().fillna(0)
        ).round(2)

        diagnostic_columns = [
            "stage_no",
            "stage",
            "source",
            "basis",
            "note",
            "evidence_seats",
            "posterior_reliability",
            "aec_coverage",
            "aec_anchor_weight",
            "missing_parties",
            "origin_retention",
            "parcel_origins",
            "ON change pp",
            *[f"{party} flow %" for party in PARTIES],
        ]

        diagnostic_columns = [
            col for col in diagnostic_columns
            if col in round_diagnostics.columns
        ]

        diagnostic_column_config = {
            col: st.column_config.NumberColumn(col, format="%.2f")
            for col in [
                "aec_coverage",
                "aec_anchor_weight",
                "origin_retention",
                "ON change pp",
                *[f"{party} flow %" for party in PARTIES],
            ]
            if col in round_diagnostics.columns
        }

        st.subheader(f"{selected_seat} Preference Flow Diagnostics")

        st.dataframe(
            round_diagnostics[diagnostic_columns],
            width="stretch",
            hide_index=True,
            column_config=diagnostic_column_config,
        )
