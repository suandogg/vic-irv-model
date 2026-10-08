from SRC.constants import PARTIES

N = len(PARTIES)

DONOR_WEIGHTS_ON = {
    "ALP": 0.15,
    "LNP": 0.45,
    "GRN": 0.05,
    "IND": 0.20,
    "OTH": 0.60,
}


def clamp01(x):
    return max(0, min(1, float(x or 0)))


def normalise_seat_class(seat_type):
    s = str(seat_type or "").strip().upper()

    if not s:
        return ""

    if s == "INNER RING":
        return "INNER_RING"
    if s == "MIDDLE RING":
        return "MIDDLE_RING"
    if s == "OUTER METRO":
        return "OUTER_METRO"
    if s == "PERI-URBAN":
        return "PERI_URBAN"
    if s == "PROVINCIAL":
        return "PROVINCIAL"
    if s == "REGIONAL":
        return "REGIONAL"

    if s == "INNERMETRO":
        return "INNERMETRO"
    if s == "OUTERMETRO":
        return "OUTERMETRO"
    if s == "RURAL":
        return "RURAL"

    return s.replace(" ", "_")


def scenario_seat_key(seat_type):
    return normalise_seat_class(seat_type)


def geo_adjust_key(seat_type):
    mapping = {
        "INNER_RING": "InnerMetro",
        "INNERMETRO": "InnerMetro",
        "MIDDLE_RING": "OuterMetro",
        "OUTER_METRO": "OuterMetro",
        "OUTERMETRO": "OuterMetro",
        "PERI_URBAN": "Provincial",
        "PROVINCIAL": "Provincial",
        "RURAL": "Rural",
        "REGIONAL": "Rural",
    }

    seat_class = normalise_seat_class(seat_type)

    return mapping.get(seat_class, str(seat_type).strip())


def alive_key(alive_parties):
    return "+".join(sorted(alive_parties))


def vector_to_dict(vec, alive):
    return {
        party: vec[i]
        for i, party in enumerate(PARTIES)
        if party in alive
    }


def uniform_alive(alive):
    k = len(alive) or 1
    return [
        1 / k if party in alive else 0
        for party in PARTIES
    ]


def normalise_alive(vec, alive):
    out = [
        max(0, float(vec[i] or 0)) if PARTIES[i] in alive else 0
        for i in range(N)
    ]

    total = sum(out)

    if total <= 0:
        return uniform_alive(alive)

    return [
        value / total if PARTIES[i] in alive else 0
        for i, value in enumerate(out)
    ]


def enforce_floor(vec, alive, scalars):
    if scalars.get("TRIAL_NO_FLOOR", False):
        return normalise_alive(vec, alive)
    min_support = float(scalars.get("MIN_SUPPORT", 0.005) or 0.005)

    out = vec.copy()

    for i, party in enumerate(PARTIES):
        if party in alive:
            out[i] = max(out[i], min_support)
        else:
            out[i] = 0

    return normalise_alive(out, alive)


def cap_shares(vec, alive, scalars):
    major_pair_max = float(scalars.get("MAJOR_PAIR_MAX", 0.90) or 0.90)
    three_way_max = float(scalars.get("THREE_WAY_MAX", 0.80) or 0.80)
    ind_oth_max = float(scalars.get("IND_OTH_MAX", 0.75) or 0.75)

    k = len(alive)

    cap = 1
    if k == 2:
        cap = major_pair_max
    elif k == 3:
        cap = three_way_max

    out = vec.copy()

    for i, party in enumerate(PARTIES):
        if party not in alive:
            out[i] = 0
        else:
            out[i] = min(out[i], cap)

    if k <= 3:
        for party in ["IND", "OTH"]:
            if party in alive:
                idx = PARTIES.index(party)
                out[idx] = min(out[idx], ind_oth_max)

    return normalise_alive(out, alive)


def apply_geo_adjust(
    vec,
    alive,
    seat_type,
    params,
    eliminated_party=None
):
    geo_table = params.get("geography_adjustments", {})
    scalars = params.get("scalar_params", {})
    key = geo_adjust_key(seat_type)

    adj = geo_table.get(key)

    if not adj:
        return vec.copy()

    strength = 1
    if (
        str(eliminated_party or "").strip().upper() == "GRN"
        and key == "Rural"
    ):
        value = scalars.get("GRN_RURAL_GEO_STRENGTH", 1)
        strength = 1 if value is None else float(value)

    non_on_strength_value = scalars.get("NON_ON_GEOGRAPHY_STRENGTH", 1.0)
    non_on_strength = (
        1.0 if non_on_strength_value is None else float(non_on_strength_value)
    )

    out = vec.copy()

    for i, party in enumerate(PARTIES):
        if party not in alive:
            out[i] = 0
            continue

        party_strength = 1.0 if party == "ON" else non_on_strength
        adjustment = float(adj.get(party, 0) or 0) * strength * party_strength
        out[i] = max(0, float(out[i] or 0) + adjustment)

    return normalise_alive(out, alive)


def apply_on_siphon(vec, alive, eliminated_party, seat_type, scalars):
    if "ON" not in alive:
        return vec.copy()

    out = vec.copy()

    strength_value = scalars.get("SIPHON_STRENGTH_ON", 0.50)
    donor_cap_value = scalars.get("SIPHON_DONOR_CAP", 0.25)
    strength = 0.50 if strength_value is None else float(strength_value)
    donor_cap = 0.25 if donor_cap_value is None else float(donor_cap_value)

    seat_class = normalise_seat_class(seat_type)

    geo_mult = 1
    if seat_class == "INNERMETRO":
        geo_mult = 0.70
    elif seat_class == "OUTERMETRO":
        geo_mult = 1.00
    elif seat_class == "PROVINCIAL":
        geo_mult = 1.15
    elif seat_class == "RURAL":
        geo_mult = 1.25

    elim = str(eliminated_party).strip().upper()

    elim_boost = 1
    if elim == "OTH":
        elim_boost = 1.25
        depletion_strength = float(
            scalars.get("OTH_ON_DONOR_DEPLETION_STRENGTH", 0.0) or 0.0
        )
        scenario_on = float(
            scalars.get("SCENARIO_ON_PRIMARY", 0.28) or 0.28
        )
        baseline_on = float(
            scalars.get("OTH_ON_DEPLETION_BASELINE", 0.28) or 0.28
        )
        reference_on = float(
            scalars.get("OTH_ON_DEPLETION_REFERENCE", 24.4) or 24.4
        )
        denominator = reference_on - baseline_on
        progress = (
            max(0.0, min(1.0, (scenario_on - baseline_on) / denominator))
            if denominator > 0 else 0.0
        )
        strength *= max(0.0, 1.0 - depletion_strength * progress)
    elif elim == "IND":
        elim_boost = 1.10
    elif elim == "LNP":
        elim_boost = 1.05
    elif elim == "GRN":
        value = scalars.get("SIPHON_ON_FROM_GRN_MULT", 0.85)
        elim_boost = 0.85 if value is None else float(value)
    elif elim == "ALP":
        elim_boost = 0.85

    total_moved = 0

    for donor, propensity in DONOR_WEIGHTS_ON.items():
        if donor not in alive:
            continue

        donor_idx = PARTIES.index(donor)
        share = float(out[donor_idx] or 0)

        if share <= 0:
            continue

        move = share * propensity * strength * geo_mult * elim_boost
        move = min(move, share * donor_cap)

        out[donor_idx] -= move
        total_moved += move

    on_idx = PARTIES.index("ON")
    out[on_idx] += total_moved

    return normalise_alive(out, alive)


def posterior_reliability(post_obj):
    if not post_obj:
        return 0
    if "__trial_reliability_override__" in post_obj:
        return clamp01(float(post_obj["__trial_reliability_override__"]))

    k = 0

    for party in PARTIES:
        if float(post_obj.get(party, 0) or 0) > 0:
            k += 1

    if k <= 2:
        return 0.15
    if k == 3:
        return 0.40
    if k == 4:
        return 0.60

    return 0.75


def with_posterior_entry(base_vec, post_vec, alive, scalars):
    post_entry_strength = float(
        scalars.get("POST_ENTRY_STRENGTH", 0.75) or 0.75
    )
    post_entry_floor = float(
        scalars.get("POST_ENTRY_FLOOR", 0.15) or 0.15
    )

    out = base_vec.copy()

    for i, party in enumerate(PARTIES):
        if party not in alive:
            continue

        if out[i] > 0:
            continue

        if post_vec[i] <= 0:
            continue

        out[i] = max(post_entry_floor, post_vec[i] * post_entry_strength)

    return normalise_alive(out, alive)


def blend_coverage_weight(coverage, scalars):
    cov_min = float(scalars.get("AEC_BLEND_COV_MIN", 0.50) or 0.50)
    cov_max = float(scalars.get("AEC_BLEND_COV_MAX", 0.90) or 0.90)
    strength = float(scalars.get("AEC_BLEND_STRENGTH", 0.75) or 0.75)

    if coverage <= cov_min:
        return 0

    if coverage >= cov_max:
        return strength

    t = (coverage - cov_min) / max(1e-9, cov_max - cov_min)

    return clamp01(t) * strength


def resolve_anchor_weight(
    coverage,
    missing_count,
    alive_count,
    eliminated_party,
    alive,
    scalars
):
    anchor_when_missing = float(
        scalars.get("AEC_ANCHOR_WHEN_MISS", 0.40) or 0.40
    )
    mismatch_max = float(
        scalars.get("AEC_MISMATCH_MAX", 0.30) or 0.30
    )
    aec_2cp_anchor_on = float(
        scalars.get("AEC_2CP_ANCHOR_ON", 0.15) or 0.15
    )

    if missing_count > 0:
        return min(
            clamp01(anchor_when_missing),
            clamp01(mismatch_max),
            0.999999
        )

    weight = blend_coverage_weight(coverage, scalars)

    if (
        eliminated_party == "ON"
        and alive_count == 2
        and "ALP" in alive
        and "LNP" in alive
    ):
        weight = max(weight, clamp01(aec_2cp_anchor_on))

    return clamp01(weight)


def get_on_special_prior(eliminated_party, alive, seat_type, params):
    alive_string = alive_key(alive)

    if alive_string not in ["ALP+ON", "LNP+ON"]:
        return None

    special = params.get("on_special_scenario_priors", {})

    seat_type_raw = str(seat_type or "").strip()

    candidate_keys = [
        f"{alive_string}|{eliminated_party}|{seat_type_raw}",
        f"{alive_string}|{eliminated_party}|{scenario_seat_key(seat_type)}",
    ]

    for key in candidate_keys:
        if key in special:
            return special[key]

    return None


def vector_stage(stage, vec, alive, note="", metadata=None):
    row = {
        "stage": stage,
        "note": note,
        **{
            party: vec[PARTIES.index(party)] if party in alive else None
            for party in PARTIES
        },
    }

    for key, value in (metadata or {}).items():
        row[key] = value

    return row


def diagnose_preference_weights(
    eliminated_party,
    alive_parties,
    matrix,
    geography_class,
    params,
    posterior=None,
    ideology=None
):
    posterior = posterior or {}
    ideology = ideology or {}

    scalars = params.get("scalar_params", {})

    elim = str(eliminated_party).strip().upper()
    alive = set(alive_parties)
    alive_arr = list(alive_parties)
    stage_rows = []
    if scalars.get("TRIAL_ON_NO_EXTRA_TRANSFORMS", False) and ("ON" in alive or elim == "ON"):
        params = dict(params)
        scalars = dict(scalars)
        scalars["SIPHON_STRENGTH_ON"] = 0
        params["scalar_params"] = scalars
        params["geography_adjustments"] = {}

    if elim not in PARTIES or not alive_arr:
        out = uniform_alive(alive)

        return {
            "eliminated_party": elim,
            "alive_parties": alive_arr,
            "seat_type": geography_class,
            "basis": "uniform",
            "final_vector": out,
            "final_flows": vector_to_dict(out, alive),
            "stages": [
                vector_stage(
                    "uniform fallback",
                    out,
                    alive,
                    "No valid eliminated party or no continuing parties.",
                )
            ],
        }

    post_key = f"{elim}|{alive_key(alive_arr)}"
    trial_obj = posterior.get(post_key)
    single_on_baseline = bool(scalars.get("TRIAL_SINGLE_ON_BASELINE", False)) and ("ON" in alive or elim == "ON")
    locked_special = single_on_baseline and get_on_special_prior(elim, alive, geography_class, params) is not None
    if isinstance(trial_obj, dict) and trial_obj.get("__federal_on_trial__") and not locked_special:
        # First calculate the complete current Victorian rule with this one
        # experimental record removed.  The trial is then a transparent
        # shrinkage blend toward that unchanged production result.
        production_posterior = dict(posterior)
        production_posterior.pop(post_key, None)
        production_params = params
        if trial_obj.get("__remove_on_siphon__"):
            production_params = dict(params)
            production_params["scalar_params"] = dict(
                params.get("scalar_params", {})
            )
            production_params["scalar_params"]["SIPHON_STRENGTH_ON"] = 0.0
        production = diagnose_preference_weights(
            eliminated_party=elim,
            alive_parties=alive_arr,
            matrix=matrix,
            geography_class=geography_class,
            params=production_params,
            posterior=production_posterior,
            ideology=ideology,
        )
        reliability = clamp01(trial_obj.get("__reliability__", 0.0))
        empirical = normalise_alive(
            [float(trial_obj.get(party, 0) or 0) for party in PARTIES],
            alive,
        )
        current = production["final_vector"]
        out = normalise_alive(
            [
                reliability * empirical[i] + (1 - reliability) * current[i]
                for i in range(N)
            ],
            alive,
        )
        stages = list(production["stages"])
        stages.append(vector_stage(
            "federal ON evidence trial",
            out,
            alive,
            "Victorian-federal exact-scenario evidence conservatively shrunk toward the complete current Victorian rule.",
            {
                "basis": "federal ON evidence trial",
                "posterior_key": post_key,
                "posterior_reliability": reliability,
                "evidence_seats": trial_obj.get("__evidence_seats__"),
                "evidence_source": trial_obj.get("__evidence_source__"),
                "on_siphon_removed": bool(trial_obj.get("__remove_on_siphon__")),
            },
        ))
        return {
            **production,
            "basis": "federal ON evidence trial",
            "final_vector": out,
            "final_flows": vector_to_dict(out, alive),
            "stages": stages,
            "trial_reliability": reliability,
        }

    raw = matrix.get(elim, {})
    base = [
        float(raw.get(party, 0) or 0)
        for party in PARTIES
    ]

    missing = [
        i for i, party in enumerate(PARTIES)
        if party in alive and not (base[i] > 0)
    ]

    total_row = sum(base)
    alive_mass = sum(
        base[i]
        for i, party in enumerate(PARTIES)
        if party in alive
    )

    aec_usable = alive_mass > 0
    aec_proj = normalise_alive(base, alive) if aec_usable else None
    coverage = alive_mass / total_row if total_row > 0 else 0
    alive_count = len(alive_arr)
    missing_parties = [
        PARTIES[i]
        for i in missing
    ]

    stage_rows.append(vector_stage(
        "raw AEC row",
        base,
        alive,
        "Original preference matrix row before filtering to continuing parties.",
        {
            "basis": "matrix",
            "aec_coverage": coverage,
            "missing_parties": ", ".join(missing_parties),
        },
    ))

    if aec_proj is not None:
        stage_rows.append(vector_stage(
            "AEC projected to alive",
            aec_proj,
            alive,
            "Raw AEC row renormalised across continuing parties.",
            {
                "basis": "matrix",
                "aec_coverage": coverage,
                "missing_parties": ", ".join(missing_parties),
            },
        ))

    on_special_vec = None
    on_special = get_on_special_prior(
        elim,
        alive,
        geography_class,
        params
    )

    if on_special:
        on_special_vec = [
            float(on_special.get(party, 0) or 0)
            if party in alive else 0
            for party in PARTIES
        ]

        on_special_vec = normalise_alive(on_special_vec, alive)
        stage_rows.append(vector_stage(
            "ON special prior",
            on_special_vec,
            alive,
            "Raw special prior for final ALP/ON or LNP/ON-style alive sets.",
            {"basis": "ON special prior"},
        ))

    if single_on_baseline:
        if on_special_vec is not None:
            out = on_special_vec
            basis = "ON special prior"
        elif aec_proj is not None:
            out = aec_proj.copy()
            basis = "single synthetic ON baseline"
        else:
            prior = ideology.get(elim, {})
            prior_vec = [float(prior.get(party, 0) or 0) if party in alive else 0 for party in PARTIES]
            out = normalise_alive(prior_vec, alive) if sum(prior_vec) > 0 else uniform_alive(alive)
            basis = "single ON baseline missing: generic prior" if sum(prior_vec) > 0 else "single ON baseline missing: uniform"
        if basis != "ON special prior":
            if scalars.get("TRIAL_MATRIX_KEEP_TRANSFORMS", False):
                out = apply_geo_adjust(out, alive, geography_class, params, eliminated_party=elim)
                out = apply_on_siphon(out, alive, elim, geography_class, scalars)
            out = enforce_floor(out, alive, scalars)
            out = cap_shares(out, alive, scalars)
        stage_rows.append(vector_stage(
            "single ON baseline trial", out, alive,
            "Special priors are locked. Use the projected synthetic row without posterior selection or extra matrix anchoring. Geography and siphon are retained only in the source-only comparison. Existing floors and caps remain; missing rows use labelled fallbacks.",
            {"basis": basis},
        ))
        return {
            "eliminated_party": elim, "alive_parties": alive_arr,
            "seat_type": geography_class, "basis": basis,
            "aec_coverage": coverage, "missing_parties": missing_parties,
            "final_vector": out, "final_flows": vector_to_dict(out, alive),
            "stages": stage_rows,
        }

    ide_vec = None
    ide_obj = ideology.get(elim)

    if ide_obj:
        ide_vec = [
            float(ide_obj.get(party, 0) or 0)
            if party in alive else 0
            for party in PARTIES
        ]

        ide_vec = normalise_alive(ide_vec, alive)
        stage_rows.append(vector_stage(
            "ideology prior",
            ide_vec,
            alive,
            "Raw fallback ideology prior.",
            {"basis": "ideology prior"},
        ))

    post_vec = None
    post_obj = posterior.get(post_key)

    if post_obj:
        post_vec = [
            float(post_obj.get(party, 0) or 0)
            if party in alive else 0
            for party in PARTIES
        ]

        if sum(post_vec) > 0:
            post_vec = normalise_alive(post_vec, alive)
            rel = posterior_reliability(post_obj)
            stage_rows.append(vector_stage(
                "posterior scenario",
                post_vec,
                alive,
                "Empirical posterior scenario before reliability blending.",
                {
                    "basis": "posterior scenario",
                    "posterior_key": post_key,
                    "posterior_reliability": rel,
                },
            ))

            if ide_vec is not None and (rel < 0.75 or "__trial_reliability_override__" in post_obj):
                post_vec = normalise_alive(
                    [
                        rel * post_vec[i] + (1 - rel) * ide_vec[i]
                        for i in range(N)
                    ],
                    alive
                )
                stage_rows.append(vector_stage(
                    "posterior + ideology blend",
                    post_vec,
                    alive,
                    "Posterior blended with ideology because scenario reliability is below 0.75.",
                    {
                        "basis": "posterior scenario",
                        "posterior_key": post_key,
                        "posterior_reliability": rel,
                    },
                ))

        else:
            post_vec = None

    if (
        aec_usable
        and len(missing) == 0
        and coverage >= 0.999
        and not (scalars.get("TRIAL_NO_SYNTHETIC_ON_PRIORITY", False) and ("ON" in alive or elim == "ON"))
    ):
        out = aec_proj.copy()
        basis = "full AEC row"
    elif post_vec is not None:
        out = post_vec
        basis = "posterior scenario"
    elif on_special_vec is not None:
        out = on_special_vec
        basis = "ON special prior"
    elif ide_vec is not None:
        out = ide_vec
        basis = "ideology prior"
    elif aec_usable and aec_proj is not None:
        out = aec_proj
        basis = "partial AEC row"
    else:
        out = uniform_alive(alive)
        basis = "uniform fallback"

    stage_rows.append(vector_stage(
        "basis selected",
        out,
        alive,
        f"Selected {basis} before final blending and transformations.",
        {"basis": basis},
    ))

    if basis == "ON special prior":
        stage_rows.append(vector_stage(
            "ON special prior locked",
            out,
            alive,
            "ON special priors are treated as calibrated scenario flows, so AEC anchoring, geography, siphon, floors, and caps are not layered on top.",
            {"basis": basis},
        ))
    else:
        if aec_usable and aec_proj is not None:
            weight = resolve_anchor_weight(
                coverage=coverage,
                missing_count=len(missing),
                alive_count=alive_count,
                eliminated_party=elim,
                alive=alive,
                scalars=scalars
            )

            out = normalise_alive(
                [
                    weight * aec_proj[i] + (1 - weight) * out[i]
                    for i in range(N)
                ],
                alive
            )
            stage_rows.append(vector_stage(
                "AEC anchor blend",
                out,
                alive,
                "Selected basis blended back toward the AEC projection.",
                {
                    "basis": basis,
                    "aec_anchor_weight": weight,
                    "aec_coverage": coverage,
                    "missing_parties": ", ".join(missing_parties),
                },
            ))

        out = apply_geo_adjust(
            out,
            alive,
            geography_class,
            params,
            eliminated_party=elim
        )
        stage_rows.append(vector_stage(
            "final geography adjustment",
            out,
            alive,
            "Final seat-type adjustment.",
            {"basis": basis},
        ))

        out = apply_on_siphon(out, alive, elim, geography_class, scalars)
        stage_rows.append(vector_stage(
            "final ON siphon",
            out,
            alive,
            "ON siphon applied once after selecting and blending the underlying preference basis.",
            {"basis": basis},
        ))

        out = enforce_floor(out, alive, scalars)
        stage_rows.append(vector_stage(
            "final minimum support floor",
            out,
            alive,
            "Final minimum support floor.",
            {"basis": basis},
        ))

        out = cap_shares(out, alive, scalars)
        stage_rows.append(vector_stage(
            "final share caps",
            out,
            alive,
            "Final cap applied for two- or three-party counts.",
            {"basis": basis},
        ))

    return {
        "eliminated_party": elim,
        "alive_parties": alive_arr,
        "seat_type": geography_class,
        "basis": basis,
        "aec_coverage": coverage,
        "missing_parties": missing_parties,
        "final_vector": out,
        "final_flows": vector_to_dict(out, alive),
        "stages": stage_rows,
    }


def get_preference_weights(
    eliminated_party,
    alive_parties,
    matrix,
    geography_class,
    params,
    posterior=None,
    ideology=None
):
    diagnostics = diagnose_preference_weights(
        eliminated_party=eliminated_party,
        alive_parties=alive_parties,
        matrix=matrix,
        geography_class=geography_class,
        params=params,
        posterior=posterior,
        ideology=ideology,
    )

    return diagnostics["final_flows"]
