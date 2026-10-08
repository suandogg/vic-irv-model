"""Five-seat fixed-primary comparison panel, independent of live app inputs."""
SEATS = ["Pakenham", "Morwell", "Pascoe Vale", "Ashwood", "Yan Yean"]
EXPLANATIONS = {
    "reference":"Unchanged reference preference rules.",
    "vec_exact_field":"Use reconstructed VEC primary-origin shares only for the matching historical non-ON field. Preserve stored synthetic ON allocation, existing ON transformations, federal blending and special priors. Native historical ON fields and unmatched fields remain reference rules.",
    "no_incomplete_matrix_anchor":"Keep existing fallback selection, but skip subsequent matrix anchoring when a continuing recipient has no positive entry. Does not infer that every zero is unobserved. All other transformations and special priors remain unchanged.",
    "oth_params_rebuild":"Rebuild only OTH synthetic rows from historical five-party rows and current OTH→ON PARAMS. Keep source selection, extra transforms, evidence blending and special priors unchanged.",
    "matrix_source_only":"Change only generic ON-related source selection to the projected matrix; retain geography/siphon, constraints, exact federal blending and locked special priors.",
    "single_on_baseline":"Use the projected synthetic matrix directly in generic ON-related calls, removing posterior/prior selection and extra geography/siphon. Exact federal blending and locked special priors remain.",
    "on_no_extra_transforms":"Keep existing source selection; remove geography and siphoning only in ON-related calls.",
    "no_on_recipient_geography":"Remove only ON's additive geography adjustment; other parties' adjustments and renormalisation remain.",
    "no_non_on_recipient_geography":"Remove other parties' geography additions; retain ON's addition. Renormalisation still links their shares.",
    "no_siphon":"Remove the generic ON preference siphon. Primary vote sourcing is unchanged.",
    "no_geography":"Remove all preference geography adjustments, not primary geography.",
    "no_constraints":"Remove minimum preference floors and destination caps.",
    "no_synthetic_priority":"Remove complete-row priority in ON-related calls. A broad sensitivity, not a provenance-aware replacement.",
    "simplified":"Combine no siphon, no preference geography, no floors/caps and no ON complete-row priority.",
    "seat_reliability_5":"Shrink ordinary posterior scenarios using evidence seats/(evidence seats+5). Federal records retain their existing reliability.",
    "seat_reliability_10":"Shrink ordinary posterior scenarios using evidence seats/(evidence seats+10). Federal records retain their existing reliability.",
    "seat_reliability_20":"Shrink ordinary posterior scenarios using evidence seats/(evidence seats+20). Federal records retain their existing reliability.",
}

def comparison_panel(results, scenario, method, matrices):
    selected=results.loc[results.Scenario.eq(scenario) & results.Variant.eq(method)].set_index("district")
    rows=[]
    for seat in SEATS:
        row=selected.loc[seat]
        rows.append({
            "Seat":seat,
            "Seat type":matrices[seat.upper()]["seat_type"],
            "Reference final two":row.matchup_reference,
            "Trial final two":row.matchup,
            "Reference winner":row.winner_reference,
            "Trial winner":row.winner,
            "Reference winning margin (pp)":100*row.margin_reference,
            "Trial winning margin (pp)":100*row.margin,
            "Reference ALP forced 2PP (%)":100*row.ALP_2PP_reference,
            "Trial ALP forced 2PP (%)":100*row.ALP_2PP,
            "ALP forced 2PP change (pp)":100*(row.ALP_2PP-row.ALP_2PP_reference),
            "Elimination order changed":row.elimination_order != row.elimination_order_reference,
            "Reference elimination order":row.elimination_order_reference,
            "Trial elimination order":row.elimination_order,
        })
    return rows
