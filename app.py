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

from SRC.loaders import load_seat_helper
from SRC.transform import build_primary_vote_table
from SRC.matrix_loader import load_synth_pref_matrices
from SRC.params_loader import load_params
from SRC.posterior_loader import load_posterior_scenarios
from SRC.ideology_loader import load_ideology_prior
from SRC.baseline_loader import load_baseline_2cp
from SRC.baseline_region_loader import load_baseline_region_summary
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


def model_baseline_swing(row, baseline_lookup):
    district = row["district"]
    winner = row["winner"]

    if district not in baseline_lookup.index:
        return None

    baseline_row = baseline_lookup.loc[district]
    winner_col = f"{winner}_2CP"

    if winner_col not in baseline_row.index:
        return None

    baseline_winner = clean_baseline_value(baseline_row[winner_col])

    if baseline_winner is None:
        return None

    current_winner = float(row["winner_pct"])

    return (current_winner - baseline_winner) * 100


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


@st.cache_data
def load_static_inputs():
    log_checkpoint("load_static_inputs start")
    seat_helper = load_seat_helper()
    log_checkpoint(f"loaded seat_helper rows={len(seat_helper)}")
    matrices = load_synth_pref_matrices()
    log_checkpoint(f"loaded matrices count={len(matrices)}")
    params = load_params()
    log_checkpoint(
        "loaded params "
        f"scalars={len(params.get('scalar_params', {}))} "
        f"specials={len(params.get('on_special_scenario_priors', {}))}"
    )
    posterior = load_posterior_scenarios()
    log_checkpoint(f"loaded posterior keys={len(posterior)}")
    ideology = load_ideology_prior()
    log_checkpoint(f"loaded ideology keys={len(ideology)}")
    baseline_2cp = load_baseline_2cp()
    log_checkpoint(f"loaded baseline_2cp rows={len(baseline_2cp)}")
    baseline_regions = load_baseline_region_summary()
    log_checkpoint(f"loaded baseline_regions rows={len(baseline_regions)}")

    return (
        seat_helper,
        matrices,
        params,
        posterior,
        ideology,
        baseline_2cp,
        baseline_regions,
    )


def apply_statewide_primary_adjustment(
    seat_helper,
    targets,
    iterations=8,
):
    adjusted = seat_helper.copy()

    for _ in range(iterations):
        current_totals = {
            party: adjusted[party].sum()
            for party in PARTIES
        }

        current_total = sum(current_totals.values())

        current_shares = {
            party: (
                current_totals[party] / current_total
                if current_total > 0 else 0
            )
            for party in PARTIES
        }

        target_total = sum(targets.values())

        target_shares = {
            party: (
                targets[party] / target_total
                if target_total > 0 else 0
            )
            for party in PARTIES
        }

        multipliers = {}

        for party in PARTIES:
            current_share = current_shares.get(party, 0)
            target_share = target_shares.get(party, 0)

            if current_share <= 0:
                multipliers[party] = 1.0
            else:
                multipliers[party] = target_share / current_share

        for party in PARTIES:
            adjusted[party] = adjusted[party] * multipliers[party]

        row_totals = adjusted[PARTIES].sum(axis=1)

        for party in PARTIES:
            adjusted[party] = adjusted[party] / row_totals

    return adjusted


def run_model(seat_helper, matrices, params, posterior, ideology, targets):
    log_checkpoint(f"run_model start targets={targets}")
    adjusted = apply_statewide_primary_adjustment(
        seat_helper,
        targets
    )
    log_checkpoint("run_model adjusted primaries")

    primary_votes = build_primary_vote_table(adjusted)
    log_checkpoint(f"run_model primary_votes rows={len(primary_votes)}")

    results = run_irv_all(
        primary_votes_df=primary_votes,
        matrices=matrices,
        params=params,
        posterior=posterior,
        ideology=ideology,
    )
    log_checkpoint(f"run_model irv complete results={len(results)}")

    return pd.DataFrame(results), adjusted


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
        lambda row: model_baseline_swing(row, baseline_lookup),
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
    seat_helper,
    matrices,
    params,
    posterior,
    ideology,
    baseline_2cp,
    baseline_regions,
) = load_static_inputs()

baseline_lookup = baseline_2cp.set_index("district")

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

INPUT_KEY_PREFIX = "statewide_primary_input_v1003"

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

if abs(total_primary - 100) > 0.01:
    st.warning(
        "Primary votes should add to 100%. "
        "The model will normalise internally."
    )

results_df, adjusted_seat_helper = run_model(
    seat_helper,
    matrices,
    params,
    posterior,
    ideology,
    targets,
)

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

alp_2pp = view_results_df["ALP_2PP"].mean() * 100
lnp_2pp = view_results_df["LNP_2PP"].mean() * 100

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


st.subheader(f"{view_title} Alternate 2PP")

alp_on_2cp = view_results_df["ALP_ON_2CP"].mean() * 100
on_alp_2cp = view_results_df["ON_ALP_2CP"].mean() * 100

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
        params=params,
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
            params=params,
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
            "basis",
            "note",
            "aec_coverage",
            "aec_anchor_weight",
            "missing_parties",
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
