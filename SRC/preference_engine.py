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
    return normalise_seat_class(seat_type)

    mapping = {
        "INNERMETRO": "InnerMetro",
        "MIDDLE_RING": "OuterMetro",
        "OUTERMETRO": "OuterMetro",
        "PROVINCIAL": "Provincial",
        "RURAL": "Rural",
        "REGIONAL": "Rural",
    }

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


def apply_geo_adjust(vec, alive, seat_type, params):
    geo_table = params.get("geography_adjustments", {})
    key = geo_adjust_key(seat_type)

    adj = geo_table.get(key)

    if not adj:
        return vec.copy()

    out = vec.copy()

    for i, party in enumerate(PARTIES):
        if party not in alive:
            out[i] = 0
            continue

        out[i] = max(0, float(out[i] or 0) + float(adj.get(party, 0) or 0))

    return normalise_alive(out, alive)


def apply_on_siphon(vec, alive, eliminated_party, seat_type, scalars):
    if "ON" not in alive:
        return vec.copy()

    out = vec.copy()

    strength = float(scalars.get("SIPHON_STRENGTH_ON", 0.50) or 0.50)
    donor_cap = float(scalars.get("SIPHON_DONOR_CAP", 0.25) or 0.25)

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
    elif elim == "IND":
        elim_boost = 1.10
    elif elim == "LNP":
        elim_boost = 1.05
    elif elim == "GRN":
        elim_boost = 0.85
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

    if (
        aec_usable
        and len(missing) == 0
        and coverage >= 0.999
    ):
        out = aec_proj.copy()
        stage_rows.append(vector_stage(
            "basis selected",
            out,
            alive,
            "AEC row fully covers all continuing parties, so no fallback source is used.",
            {"basis": "full AEC row"},
        ))

        out = apply_geo_adjust(out, alive, geography_class, params)
        stage_rows.append(vector_stage(
            "geography adjustment",
            out,
            alive,
            "Seat-type adjustment applied to the selected flow.",
            {"basis": "full AEC row"},
        ))

        out = apply_on_siphon(out, alive, elim, geography_class, scalars)
        stage_rows.append(vector_stage(
            "ON siphon",
            out,
            alive,
            "Additional movement toward ON when ON is still alive.",
            {"basis": "full AEC row"},
        ))

        out = enforce_floor(out, alive, scalars)
        stage_rows.append(vector_stage(
            "minimum support floor",
            out,
            alive,
            "Minimum support floor applied to continuing parties.",
            {"basis": "full AEC row"},
        ))

        out = cap_shares(out, alive, scalars)
        stage_rows.append(vector_stage(
            "share caps",
            out,
            alive,
            "Final cap applied for two- or three-party counts.",
            {"basis": "full AEC row"},
        ))

        return {
            "eliminated_party": elim,
            "alive_parties": alive_arr,
            "seat_type": geography_class,
            "basis": "full AEC row",
            "aec_coverage": coverage,
            "missing_parties": missing_parties,
            "final_vector": out,
            "final_flows": vector_to_dict(out, alive),
            "stages": stage_rows,
        }

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
        on_special_vec = enforce_floor(on_special_vec, alive, scalars)
        on_special_vec = cap_shares(on_special_vec, alive, scalars)
        stage_rows.append(vector_stage(
            "ON special prior",
            on_special_vec,
            alive,
            "Special prior for final ALP/ON or LNP/ON-style alive sets.",
            {"basis": "ON special prior"},
        ))

    ide_vec = None
    ide_obj = ideology.get(elim)

    if ide_obj:
        ide_vec = [
            float(ide_obj.get(party, 0) or 0)
            if party in alive else 0
            for party in PARTIES
        ]

        ide_vec = normalise_alive(ide_vec, alive)
        ide_vec = apply_geo_adjust(ide_vec, alive, geography_class, params)
        ide_vec = enforce_floor(ide_vec, alive, scalars)
        ide_vec = cap_shares(ide_vec, alive, scalars)
        stage_rows.append(vector_stage(
            "ideology prior",
            ide_vec,
            alive,
            "Fallback ideology prior after geography adjustment, floor, and caps.",
            {"basis": "ideology prior"},
        ))

    post_vec = None
    post_key = f"{elim}|{alive_key(alive_arr)}"
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

            if ide_vec is not None and rel < 0.75:
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

            post_vec = apply_geo_adjust(post_vec, alive, geography_class, params)
            stage_rows.append(vector_stage(
                "posterior geography adjustment",
                post_vec,
                alive,
                "Seat-type adjustment applied to posterior path.",
                {"basis": "posterior scenario"},
            ))

            post_vec = with_posterior_entry(post_vec, post_vec, alive, scalars)
            stage_rows.append(vector_stage(
                "posterior entry floor",
                post_vec,
                alive,
                "Adds support for parties present in posterior but absent from the base vector.",
                {"basis": "posterior scenario"},
            ))

            post_vec = enforce_floor(post_vec, alive, scalars)
            post_vec = cap_shares(post_vec, alive, scalars)
            stage_rows.append(vector_stage(
                "posterior floor/caps",
                post_vec,
                alive,
                "Posterior path after minimum support floor and caps.",
                {"basis": "posterior scenario"},
            ))
        else:
            post_vec = None

    if post_vec is not None:
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

    if post_vec is not None:
        out = with_posterior_entry(out, post_vec, alive, scalars)
        stage_rows.append(vector_stage(
            "selected posterior entry floor",
            out,
            alive,
            "Posterior entry floor applied again to selected posterior path.",
            {"basis": basis},
        ))

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

    out = apply_geo_adjust(out, alive, geography_class, params)
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
