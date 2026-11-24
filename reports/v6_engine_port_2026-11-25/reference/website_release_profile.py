"""Approved website-only final profile; archived/default model inputs stay frozen."""
from copy import deepcopy
import math
import inspect

ON_ALPHA = 0.8
LEGACY_PROFILE_ID = "website-final-2026-11-27-on-alpha-0.8"
TWO_OFFSET_PROFILE_ID = "website-final-2026-11-27-sa-preferences-v1"
FOUR_OFFSET_PROFILE_ID = "website-final-2026-11-27-sa-preferences-v2"
V3_PROFILE_ID = "website-interim-2026-11-24-calibrated-uncertainty-v3"
V4_PROFILE_ID = "website-interim-2026-11-24-input-corrections-v4"
V5_PROFILE_ID = "website-interim-2026-11-24-integrity-v5"
PROFILE_ID = "website-interim-2026-11-24-integrity-v6"
# Owner review, 23 Nov 2026 (../reports/integrity_sweep_2026-11-22/v6/). v6 = v5 with: metro Liberal->One Nation
# seat-level SA targets replacing the C1 offsets (applied before the simulation draw, generic SD); One Nation
# exclusion rule replacing C2a; metro Labor-excluded LNP+ON special prior 22.1%; South Barwon/Ringwood/Narracan
# input fixes; siphon class names and the AEC_ANCHOR_WHEN_MISSING key read as documented.
# Integrity sweep, 22-23 Nov 2026 (../reports/integrity_sweep_2026-11-22/). v5 = v4 + evidence offsets
# replacing material placeholder flows (smallest log-odds offset removing the pooled gap to the evidence,
# halving rule below 20 contests unless independently corroborated). Applied after every other flow layer.
# Final pre-interim audit, 22 Nov 2026 (../reports/final_audit_2026-11-22/). Input-only bug
# fixes through existing mechanisms; v3 exponent, offsets and uncertainty are unchanged.
#  1. LOWER_LNP_PRECOLLAPSE is Liberal/National count leakage (two Coalition candidates):
#     off for the five 2026 single-Coalition seats; Ripon added at the mean 2022 leakage.
#  2. Registered VEC 2026 cards: Greens open cards also in Eureka, Hawthorn, Morwell; Labor
#     open ticket in Albert Park; Liberal open cards in Brunswick and Footscray = half shift.
#  3. Owner: Hawthorn community-independent successor retains the reviewed 2022 strength.
PRECOLLAPSE_SINGLE_COALITION_2026 = ("Bass", "Euroa", "Mildura", "Morwell", "Shepparton")
PRECOLLAPSE_MEAN_2022_LEAKAGE = round((0.0954 + 0.0528 + 0.0974 + 0.0455 + 0.0916) / 5, 6)
INPUT_CORRECTIONS = {
    "lnp_precollapse": {"disable": list(PRECOLLAPSE_SINGLE_COALITION_2026),
                        "add": {"Ripon": {"ON": round(PRECOLLAPSE_MEAN_2022_LEAKAGE * .65, 7),
                                          "ALP": round(PRECOLLAPSE_MEAN_2022_LEAKAGE * .35, 7),
                                          "LNP": round(1 - PRECOLLAPSE_MEAN_2022_LEAKAGE, 6)}}},
    "htv_review": {"greens_seats_add": ["Eureka", "Hawthorn", "Morwell"],
                   "labor_open_seats_add": ["Albert Park"]},
    "htv_deal": {"exceptions": [], "half_shift_seats": ["Brunswick", "Footscray"]},
    # The frozen reviewed row already has median/p10/p90 17.183/7.433/32.429.
    # brand/brand_share are correlation controls, not a successor strength rule.
    "candidate_field": {"reviewed_remove": [], "reviewed_upsert": [['Hawthorn', 'hawthorn_shima_ibuki', 'Shima Ibuki', 'entrant', 'IND', '17.183', '7.433', '32.429', '', '', '19.98', 'Reviewed 12 Nov 2026 (Callum): teal successor treated as the returning Hawthorn independent. Lowe 19.98% (2022) times retention 0.86 (10-90%: 0.37-1.62); teal support follows the movement, not the candidate.']],
                        "default_remove": ["hawthorn_ibuki_shima"], "default_add": []},
}
# v6 input fixes (owner, 23 Nov 2026).
#  South Barwon: 2022 Labor MP (Cheeseman) not on the 2026 ballot -> Labor retiring flag.
#  Ringwood: 2022 winner Labor (Fowles) -> held-by ALP; Fowles not on the 2026 ballot -> Labor retiring flag (owner, 23 Nov).
#  Narracan: no 2022 general election (supplementary Jan 2023, no Labor candidate). Lean rebuilt with the
#  standard 75/25 formula, the 2018 VEC result reconstructed on 2022 boundaries (21 Nov booth reconstruction,
#  reports/vic2022_backtest_2026-11-21) standing in for the missing 2022 general election: lean = 2018 notional
#  share - 2018 statewide share (One Nation folded into Other, as in 2018).
NARRACAN_LEANS = {"ALP_pvi": "-0.111432", "LNP_pvi": "0.206104", "GRN_pvi": "-0.046794", "IND_pvi": "0.003823", "OTH_pvi": "-0.051702"}
V6_INPUT_CORRECTIONS = dict(deepcopy(INPUT_CORRECTIONS),
                            seat_adjustments={"South Barwon|ALP": {"retiring_incumbent": "TRUE"},
                                              "Ringwood|LNP": {"party": "ALP", "retiring_incumbent": "TRUE"}},
                            legacy_primary_inputs={"Ringwood": {"held_by": "ALP"}, "Narracan": dict(NARRACAN_LEANS)})
CORRECTED_EXPERIMENT_KEYS = ("candidate_field", "htv_deal", "htv_review")
_METRO = ["Inner Ring", "Middle Ring", "Outer Metro"]
_ALL = _METRO + ["Peri-urban", "Provincial", "Regional"]
_CARD_EXCEPTIONS = {"GREENVALE": 0.0, "PRESTON": 0.0, "BRUNSWICK": 0.5, "FOOTSCRAY": 0.5}
# context: "pair" (two continuing), "multi" (three or more) or an exact sorted continuing set.
V5_EVIDENCE_OFFSETS = [
    # C1 metro Liberal exclusions -> One Nation: SA 2026 metro (13 three-way, 7 final-pair contests;
    # 22 overall), composition-matched to the Victorian class mix. Liberal cards: Greenvale/Preston rank
    # Labor above One Nation (no increase); Brunswick/Footscray open (half).
    {"id": "C1-multi", "donor": "LNP", "recipient": "ON", "classes": _METRO, "context": "multi", "offset": 0.779922, "seat_factor": _CARD_EXCEPTIONS},
    {"id": "C1-pair", "donor": "LNP", "recipient": "ON", "classes": _METRO, "context": "pair", "offset": 0.326999, "seat_factor": _CARD_EXCEPTIONS},
    # C2a One Nation exclusions -> Coalition: VEC 2022 exact fields + federal 2025 Victorian pooled.
    {"id": "C2a-ALP+LNP", "donor": "ON", "recipient": "LNP", "classes": _ALL, "context": "ALP+LNP", "offset": 0.187933, "seat_factor": {}},
    {"id": "C2a-ALP+GRN+IND+LNP", "donor": "ON", "recipient": "LNP", "classes": _ALL, "context": "ALP+GRN+IND+LNP", "offset": 0.0995, "seat_factor": {}},
    {"id": "C2a-ALP+IND+LNP", "donor": "ON", "recipient": "LNP", "classes": _ALL, "context": "ALP+IND+LNP", "offset": -0.398, "seat_factor": {}},
    # C2b (metro Greens exclusions -> One Nation, SA 2026 metro) is reported, not applied: below the
    # materiality threshold alone and the owner retained Greens handling on 20 Nov 2026.
    # C2c metro independent exclusions -> One Nation: SA 2026 metro (12 contests, halved).
    {"id": "C2c-ALP+GRN+LNP+ON", "donor": "IND", "recipient": "ON", "classes": _METRO, "context": "ALP+GRN+LNP+ON", "offset": -0.164, "seat_factor": {}},
    {"id": "C2c-ALP+ON", "donor": "IND", "recipient": "ON", "classes": _METRO, "context": "ALP+ON", "offset": 0.5295, "seat_factor": {}},
]
# v6 offsets (post-draw, as v3/v5). C1 offsets replaced by LNP_ON_TARGETS; C2a replaced by the owner's One Nation
# exclusion rule: target = directed-card level (VEC 2022 exact fields + federal 2025 Victorian), SA 2026 (open
# cards) the floor; raise PRISM only if below (halfway if <20 directed contests, never below the floor); keep if above.
EVIDENCE_OFFSETS = [
    {"id": "S2-ALP+LNP", "donor": "ON", "recipient": "LNP", "classes": _ALL, "context": "ALP+LNP", "offset": 0.091471, "seat_factor": {}},          # n=4 halfway: 77.10 -> 78.67 (target 80.23)
    {"id": "S2-ALP+GRN+LNP", "donor": "ON", "recipient": "LNP", "classes": _ALL, "context": "ALP+GRN+LNP", "offset": 0.1856, "seat_factor": {}},   # n=20 full; SA floor 66.47 binds over directed 61.32
    {"id": "S2-ALP+GRN+LNP+OTH", "donor": "ON", "recipient": "LNP", "classes": _ALL, "context": "ALP+GRN+LNP+OTH", "offset": 0.013371, "seat_factor": {}},  # n=6 halfway
    {"id": "S2-ALP+GRN+IND+LNP", "donor": "ON", "recipient": "LNP", "classes": _ALL, "context": "ALP+GRN+IND+LNP", "offset": 0.098842, "seat_factor": {}},  # n=8 halfway
    V5_EVIDENCE_OFFSETS[5], V5_EVIDENCE_OFFSETS[6],  # C2c unchanged
]
# Step 1: metro Liberal exclusions, effective One Nation share set to SA 2026 metro (class value where SA has >=5
# contests in that class and context, else pooled metro). Applied after the deal shift and before the simulation
# draw; other recipients keep their relative shares. Card exceptions: Greenvale/Preston unchanged, Brunswick/
# Footscray halfway. Draw SD for these flows: generic (PREF_GENERIC_LOG_SD).
LNP_ON_TARGETS = {"donor": "LNP", "recipient": "ON",
                  "multi": {"Inner Ring": 0.511139, "Middle Ring": 0.529125, "Outer Metro": 0.5013},
                  "pair": {"Inner Ring": 0.63476, "Middle Ring": 0.63476, "Outer Metro": 0.63476},
                  "seat_factor": dict(_CARD_EXCEPTIONS), "sd": "generic"}
TARGET_KEY = "_website_flow_targets"
# Step 4: metro Labor-excluded LNP+ON special prior, SA 2026 regional Labor exclusions (cards put One Nation last).
SPECIAL_PRIOR_OVERRIDES = {f"LNP+ON|ALP|{c}": {"ALP": None, "LNP": 0.779, "ON": 0.221} for c in _METRO}
SIPHON_FIX_KEY = "WEBSITE_SIPHON_CLASS_NAMES"
# Legacy siphon class names (INNERMETRO/RURAL) mapped to the current classes; intended 0.70 / 1.25.
SIPHON_CLASS_ALIASES = {"INNER RING": "INNERMETRO", "REGIONAL": "RURAL"}
EVIDENCE_KEY = "_website_evidence_offsets"
MAJOR_RESIDUAL_FACTOR = 1.624653
INDEPENDENT_OTHER_RESIDUAL_FACTOR = 3.975
STATEWIDE_SD_PP = {"ALP": 2.58324923279813, "LNP": 2.58324923279813,
                   "GRN": 1.4686042013221317, "ON": 2.134003178186207,
                   "IND": 0.8618931878317271, "OTH": 0.8618931878317271}
EFFECTIVE_STATEWIDE_SD_PP = {"major": 2.2465966802073125, "Greens": 1.4269820523670846,
                             "One Nation": 1.906408128922815, "other": 1.6996731711975948}
OFFSET_CLASSES = ("Peri-urban", "Provincial", "Regional")
PREFERENCE_OFFSETS = {"ALP": 0.736478, "LNP": 0.450609, "IND": 0.745884, "OTH": 0.981510}
OFFSET_KEY = "_website_on_preference_offsets"


def v3_profile_metadata():
    return {"id": V3_PROFILE_ID, "scalar_overrides": {"ON alpha": ON_ALPHA},
            "preference_offsets": {"classes": list(OFFSET_CLASSES), "by_donor": dict(PREFERENCE_OFFSETS)},
            "uncertainty": {"statewide_sd_pp": dict(STATEWIDE_SD_PP),
                            "effective_statewide_sd_pp": dict(EFFECTIVE_STATEWIDE_SD_PP),
                            "local_regional_factors": {p: INDEPENDENT_OTHER_RESIDUAL_FACTOR if p in ("IND", "OTH") else MAJOR_RESIDUAL_FACTOR for p in STATEWIDE_SD_PP}}}


def v4_profile_metadata():
    return dict(v3_profile_metadata(), id=V4_PROFILE_ID, input_corrections=deepcopy(INPUT_CORRECTIONS))


def v5_profile_metadata():
    return dict(v4_profile_metadata(), id=V5_PROFILE_ID, evidence_offsets=deepcopy(V5_EVIDENCE_OFFSETS))


def profile_metadata():
    return dict(v4_profile_metadata(), id=PROFILE_ID, input_corrections=deepcopy(V6_INPUT_CORRECTIONS),
                evidence_offsets=deepcopy(EVIDENCE_OFFSETS), lnp_on_targets=deepcopy(LNP_ON_TARGETS),
                special_prior_overrides=deepcopy(SPECIAL_PRIOR_OVERRIDES),
                engine_fixes={"siphon_class_names": dict(SIPHON_CLASS_ALIASES), "anchor_key": "AEC_ANCHOR_WHEN_MISSING"})


def prepare_matrices(matrices, params):
    """Tag each seat matrix with its district (seat-level card exceptions). Results are unchanged
    unless the run's parameters carry evidence offsets; untagged/unmarked runs pass through."""
    if not params.get(EVIDENCE_KEY) and not params.get(TARGET_KEY):
        return matrices
    return {k: dict(item, matrix=dict(item["matrix"], __district__=k)) for k, item in matrices.items()}


def shift_recipient(flows, recipient, d):
    q = flows.get(recipient, 0.0)
    if not 0 < q < 1 or d == 0:
        return flows
    f = math.exp(d)
    new = q * f / (1 - q + q * f)
    scale = (1 - new) / (1 - q)
    return {p: new if p == recipient else v * scale for p, v in flows.items()}


def evidence_flows(flows, donor, seat_class, matrix, rules):
    """Apply v5 evidence offsets for one excluded party; other recipients rescale proportionally."""
    if not rules:
        return flows
    norm = lambda s: str(s).strip().upper()
    alive = "+".join(sorted(flows))
    seat = norm(matrix.get("__district__", ""))
    out = flows
    for r in rules:
        if r["donor"] != donor or r["recipient"] not in out or norm(seat_class) not in {norm(c) for c in r["classes"]}:
            continue
        c = r["context"]
        if (c == "pair" and len(out) != 2) or (c == "multi" and len(out) < 3) or (c not in ("pair", "multi") and c != alive):
            continue
        out = shift_recipient(out, r["recipient"], r["offset"] * r["seat_factor"].get(seat, 1.0))
    return out


def target_flows(flows, donor, seat_class, matrix, config):
    """Step 1 (v6): set the recipient's share to the class/context target; others keep relative shares."""
    if not config or donor != config["donor"] or config["recipient"] not in flows or len(flows) < 2:
        return flows
    table = config["pair" if len(flows) == 2 else "multi"]
    cls = next((c for c in table if c.strip().upper() == str(seat_class).strip().upper()), None)
    if cls is None:
        return flows
    factor = config["seat_factor"].get(str(matrix.get("__district__", "")).strip().upper(), 1.0)
    q = flows[config["recipient"]]
    new = q + factor * (table[cls] - q)
    if factor == 0 or not 0 <= q < 1 or abs(new - q) < 1e-15:
        return flows
    scale = (1 - new) / (1 - q)
    return {p: new if p == config["recipient"] else v * scale for p, v in flows.items()}


# C3: accurate source labels. The frozen engine's category says "Victorian preference evidence"
# for any full matrix row, including the synthetic One Nation share.
def describe_basis(diagnostic, eliminated, alive):
    b = diagnostic["basis"]
    on = "ON" in alive
    vec = any(s.get("vec_exact_field_matched") for s in diagnostic["stages"])
    if b == "ON special prior":
        return "Hand-set One Nation final-pair prior (no direct evidence)"
    if b == "federal ON evidence trial":
        w = next((s.get("posterior_reliability") for s in reversed(diagnostic["stages"]) if s.get("posterior_reliability") is not None), None)
        return f"Federal 2025 Victorian evidence ({100 * w:.0f}% weight) blended with the model's prior rule" if w is not None else "Federal 2025 evidence blended with the model's prior rule"
    if b == "full AEC row":
        if eliminated == "ON":
            return "Synthetic One Nation row (seat-class prior, not observed)"
        if vec:
            return "2022 VEC row with synthetic One Nation share" if on else "2022 VEC exact field"
        return "2022 Victorian matrix row with synthetic One Nation share" if on else "2022 Victorian matrix row"
    if b == "posterior scenario":
        return "VEC 2022 alive-set scenario (small sample) blended with ideology prior"
    if b == "ideology prior":
        return "Generic ideology prior (no direct evidence)"
    if b == "partial AEC row":
        return "Partial 2022 matrix row"
    return "Uniform fallback"


def _rewrite_csv(path, transform):
    import csv
    text = path.read_text()
    rows = list(csv.reader(text.splitlines()))
    new = transform([list(r) for r in rows])
    if new == rows:
        return False
    import io
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n" if "\r\n" not in text else "\r\n").writerows(new)
    path.write_text(buffer.getvalue())
    return True


def apply_input_corrections(model, corrections):
    """Idempotently correct restored model input files; returns changed relative paths.

    Only the seat rows named in the recorded corrections change. Nothing in SRC is edited.
    """
    from pathlib import Path
    model, changed = Path(model), []
    pre = corrections.get("lnp_precollapse")
    if pre:
        def precollapse(rows):
            head = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Electorate")
            cols = rows[head]
            e, d, s, en = (cols.index(c) for c in ("Electorate", "DestinationCategory", "Share", "Enabled"))
            disable = {x.upper() for x in pre["disable"]}
            out = []
            for r in rows:
                r = list(r)
                if len(r) > en and r[e].strip().upper() in disable:
                    r[en] = "FALSE"
                out.append(r)
            for seat, shares in pre["add"].items():
                if any(not math.isfinite(v) or not 0 <= v <= 1 for v in shares.values()) or abs(sum(shares.values()) - 1) > 1e-9:
                    raise ValueError('Invalid Coalition correction shares: '+seat)
                # A new candidate may start from an older corrected snapshot.
                # Replace only this seat's rows, making multi-destination updates idempotent.
                out = out[:head + 1] + [r for r in out[head + 1:] if not (len(r) > e and r[e].strip().upper() == seat.upper())]
                for dest, share in shares.items():
                    row = [""] * len(cols)
                    values = {"Electorate": seat, "OriginCategory": "LNP", "DestinationCategory": dest,
                              "Share": f"{100 * share:.4f}%", "FrontierRound": "",
                              "CandidateSubtypeMix": "LIB|NAT (2026 ballot)", "Enabled": "TRUE",
                              "Strength": "100.00%", "ManualOverrideShare": "",
                              "Source": "Owner 22 Nov 2026: mean 2022 leakage; Ripon ON/ALP 65/35, anchored to SA regional exclusions"}
                    for k, v in values.items():
                        if k in cols:
                            row[cols.index(k)] = v
                    out.append(row)
            return out
        if _rewrite_csv(model / "data/raw/LOWER_LNP_PRECOLLAPSE.csv", precollapse):
            changed.append("data/raw/LOWER_LNP_PRECOLLAPSE.csv")
    cf = corrections.get("candidate_field")
    if cf:
        folder = model / "data/development/candidate_field"
        drop = set(cf.get("reviewed_remove", []))
        def reviewed(rows):
            updates = {r[1]: list(r) for r in cf.get("reviewed_upsert", [])}
            out = [r for r in rows if not (len(r) > 1 and r[1] in drop)]
            found = set()
            for i, r in enumerate(out):
                if len(r) > 1 and r[1] in updates:
                    out[i] = updates[r[1]]; found.add(r[1])
            return out + [r for key, r in updates.items() if key not in found]
        if _rewrite_csv(folder / "REVIEWED_CANDIDATES.csv", reviewed):
            changed.append("data/development/candidate_field/REVIEWED_CANDIDATES.csv")
        def defaults(rows):
            drop_defaults = set(cf.get("default_remove", []))
            rows = [r for r in rows if not (len(r) > 1 and r[1] in drop_defaults)]
            ids = {r[1] for r in rows if len(r) > 1}
            return rows + [list(r) for r in cf.get("default_add", []) if r[1] not in ids]
        if _rewrite_csv(folder / "DEFAULT_IND_STRENGTHS.csv", defaults):
            changed.append("data/development/candidate_field/DEFAULT_IND_STRENGTHS.csv")
    for key, name, keycols in (("seat_adjustments", "data/raw/LOWER_SEAT_ADJUSTMENTS.csv", ("district", "party")),
                               ("legacy_primary_inputs", "data/raw/LEGACY_PRIMARY_INPUTS.csv", ("district",))):
        edits = corrections.get(key)
        if not edits:
            continue
        def edit(rows, edits=edits, keycols=keycols):
            head = [c.strip() for c in rows[0]]
            idx = [head.index(c) for c in keycols]
            found, out = set(), [list(rows[0])]
            for r in rows[1:]:
                r = list(r)
                k = "|".join(r[i].strip() for i in idx) if len(r) > max(idx) else None
                if k in edits:
                    found.add(k)
                    for col, value in edits[k].items():
                        r[head.index(col)] = value
                out.append(r)
            missing = set(edits) - found
            if missing:
                # Idempotent: a re-keyed row (Ringwood party) may already be corrected.
                done = {"|".join(r[i].strip() for i in idx) for r in out[1:] if len(r) > max(idx)}
                if any(not any(d.split("|")[0] == m.split("|")[0] for d in done) for m in missing):
                    raise ValueError(f"Input correction rows not found in {name}: {sorted(missing)}")
            return out
        if _rewrite_csv(model / name, edit):
            changed.append(name)
    return changed


def corrected_htv_configs(corrections, load_htv_deal_config, load_htv_review_config, review_defaults):
    """Build the deal/review configs through their own loaders and validators."""
    deal = load_htv_deal_config(exceptions=tuple(corrections["htv_deal"]["exceptions"]))
    for seat in corrections["htv_deal"]["half_shift_seats"]:
        own = deal["seat_liberal_shifts"].get(seat.upper(), deal["liberal_shift"])
        deal["seat_liberal_shifts"][seat.upper()] = round(own / 2, 6)
    review_add = corrections["htv_review"]
    review = load_htv_review_config(
        greens_seats=tuple(review_defaults["greens_seats"]) + tuple(review_add["greens_seats_add"]),
        labor_open_seats=tuple(review_defaults["labor_open_seats"]) + tuple(review_add["labor_open_seats_add"]))
    from SRC.htv_deal import validate_config
    return validate_config(deal), review


def input_corrections_for_run(*, replay=False, recorded_profile=None, new_candidate=False):  # v4 and v5 share corrections
    """Recorded corrections for replays; today's only for a new website candidate."""
    if new_candidate:
        return deepcopy(V6_INPUT_CORRECTIONS)
    if replay and recorded_profile and "input_corrections" in recorded_profile:
        return deepcopy(recorded_profile["input_corrections"])
    return None


def apply_website_release_profile(params, evidence=True, version="v6"):
    """Copy the approved exponent, four preference offsets and evidence layers into a candidate.

    evidence=False gives v3/v4 parameters; version "v5" the 23 Nov prepared profile; "v6" the current one."""
    result = deepcopy(params)
    if "ON alpha" not in result["scalar_params"]:
        raise ValueError("Website release profile requires scalar parameter ON alpha")
    result["scalar_params"]["ON alpha"] = ON_ALPHA
    result[OFFSET_KEY] = deepcopy(profile_metadata()["preference_offsets"])
    if not evidence:
        return result
    if version == "v5":
        result[EVIDENCE_KEY] = deepcopy(V5_EVIDENCE_OFFSETS)
        return result
    if version != "v6":
        raise ValueError(f"Unknown website profile version: {version}")
    result[EVIDENCE_KEY] = deepcopy(EVIDENCE_OFFSETS)
    result[TARGET_KEY] = deepcopy(LNP_ON_TARGETS)
    special = result.setdefault("on_special_scenario_priors", {})
    for key, value in SPECIAL_PRIOR_OVERRIDES.items():
        if key not in special:
            raise ValueError(f"Missing ON special prior: {key}")
        special[key] = dict(value)
    scalars = result["scalar_params"]
    if "AEC_ANCHOR_WHEN_MISSING" in scalars:  # documented key; the frozen code reads AEC_ANCHOR_WHEN_MISS
        scalars["AEC_ANCHOR_WHEN_MISS"] = scalars["AEC_ANCHOR_WHEN_MISSING"]
    scalars[SIPHON_FIX_KEY] = 1.0
    return result


def parameters_for_run(params, *, replay=False, recorded_profile=None, new_candidate=False):
    """Restore the recorded profile, never today's settings onto an old replay."""
    legacy = {"id": LEGACY_PROFILE_ID, "scalar_overrides": {"ON alpha": ON_ALPHA}}
    two = {"id": TWO_OFFSET_PROFILE_ID, "scalar_overrides": {"ON alpha": ON_ALPHA},
           "preference_offsets": {"classes": list(OFFSET_CLASSES), "by_donor": {"ALP": .736478, "LNP": .450609}}}
    four = {"id": FOUR_OFFSET_PROFILE_ID, "scalar_overrides": {"ON alpha": ON_ALPHA},
            "preference_offsets": {"classes": list(OFFSET_CLASSES), "by_donor": dict(PREFERENCE_OFFSETS)}}
    if recorded_profile is not None and recorded_profile not in (legacy, two, four, v3_profile_metadata(), v4_profile_metadata(), v5_profile_metadata(), profile_metadata()):
        raise ValueError("Unsupported frozen website release profile")
    if new_candidate or not replay or recorded_profile == profile_metadata():
        return apply_website_release_profile(params), profile_metadata()
    if recorded_profile == v5_profile_metadata():
        return apply_website_release_profile(params, version="v5"), v5_profile_metadata()
    if recorded_profile == v4_profile_metadata():
        return apply_website_release_profile(params, evidence=False), v4_profile_metadata()
    if recorded_profile == v3_profile_metadata():
        return apply_website_release_profile(params, evidence=False), v3_profile_metadata()
    if recorded_profile == four:
        return apply_website_release_profile(params, evidence=False), deepcopy(four)
    if recorded_profile == two:
        result = apply_website_release_profile(params, evidence=False)
        result[OFFSET_KEY] = deepcopy(two["preference_offsets"])
        return result, deepcopy(two)
    if recorded_profile == legacy:
        result = deepcopy(params)
        result["scalar_params"]["ON alpha"] = ON_ALPHA
        return result, deepcopy(legacy)
    return params, None



def apply_uncertainty_profile(settings, experiment, recorded_profile):
    """Copy approved uncertainty onto fresh, unprofiled saved settings/budgets.

    Old recorded profiles and unmarked historical runs retain their original
    settings. Call once on raw loader inputs, not an already-scaled experiment.
    Correlations, class noise, donor/concentration and preferences are untouched.
    """
    result, config = deepcopy(settings), deepcopy(experiment)
    if not recorded_profile or "uncertainty" not in recorded_profile:
        return result, config
    if recorded_profile not in (v3_profile_metadata(), v4_profile_metadata(), v5_profile_metadata(), profile_metadata()):
        raise ValueError("Unsupported frozen website uncertainty profile")
    approved = recorded_profile["uncertainty"]
    budget = config["structured_nowcast"]
    for party, sd in approved["statewide_sd_pp"].items():
        key = f"STATEWIDE_SD_{party}_PP"
        if key not in result:
            raise ValueError(f"Missing website statewide uncertainty setting: {key}")
        result[key] = sd
    for field in ("local_sd_pp", "region_sd_pp"):
        if set(budget[field]) != set(approved["local_regional_factors"]):
            raise ValueError(f"Incomplete website residual budget: {field}")
        budget[field] = {p: value * approved["local_regional_factors"][p]
                         for p, value in budget[field].items()}
    return result, config

def offset_flows(flows, donor, seat_class, config):
    """Reduce only the approved ON-receipt odds; preserve other recipient ratios."""
    normal = lambda s: str(s).strip().upper().replace('-', '_').replace(' ', '_')
    if not config or donor not in config['by_donor'] or normal(seat_class) not in {normal(c) for c in config['classes']}:
        return flows
    q = flows.get('ON', 0.0)
    if not 0 < q < 1:
        return flows
    factor = math.exp(-config['by_donor'][donor])
    changed = q * factor / (1 - q + q * factor)
    scale = (1 - changed) / (1 - q)
    return {p: changed if p == 'ON' else v * scale for p, v in flows.items()}


def _targeted(frozen, pe):
    """Insert v6 flow targets after the deal shift and before the simulation draw (pass-through otherwise).

    The frozen wrapper runs unshocked (central flow incl. the deal shift); the target is applied; the draw is
    then perturbed as the frozen wrapper does, with the generic preference SD for targeted flows."""
    signature = inspect.signature(frozen)
    def targeted(*args, **kwargs):
        b = signature.bind(*args, **kwargs).arguments
        params = b["params"]
        config = params.get(TARGET_KEY)
        if not config or b["eliminated_party"] != config["donor"]:
            return frozen(*args, **kwargs)
        shocks = params.get("_forecast_preference_shocks")
        cache = params.get("_forecast_flow_cache")
        key = ("website-target", b["eliminated_party"], tuple(sorted(b["alive_parties"])), id(b["matrix"]),
               b["geography_class"], id(b.get("posterior")), id(b.get("ideology")))
        if cache is not None and key in cache:
            return cache[key]
        central = {k: v for k, v in params.items() if k not in ("_forecast_preference_shocks", "_forecast_flow_cache")}
        b = dict(b, params=central)
        result = frozen(**b)
        flows = target_flows(result["final_flows"], b["eliminated_party"], b["geography_class"], b["matrix"], config)
        if flows is not result["final_flows"]:
            vector = [flows.get(p, 0.0) for p in pe.PARTIES]
            result = dict(result, final_flows=flows, final_vector=vector, flow_target=True,
                          stages=list(result["stages"]) + [pe.vector_stage(
                              "SA 2026 metro target", vector, set(b["alive_parties"]),
                              "Owner 23 Nov 2026: Liberal->One Nation share set to the SA 2026 metro level for this class and count context.")])
        if shocks is not None:
            from SRC.forecast_engine import perturb_preference_flows
            probe = dict(result, basis="generic preference SD", stages=[]) if result.get("flow_target") else result
            drawn = perturb_preference_flows(probe, b["eliminated_party"], b["geography_class"], shocks)
            vector = [drawn.get(p, 0.0) for p in pe.PARTIES]
            result = dict(result, final_flows=drawn, final_vector=vector, stages=list(result["stages"]) + [pe.vector_stage(
                "forecast preference draw", vector, set(b["alive_parties"]),
                "Simulation-only correlated uncertainty around the central flow; source rows unchanged.")])
        if cache is not None:
            cache[key] = result
        return result
    targeted.__signature__ = signature
    return targeted


def install_preference_runtime():
    """Adapt process-local frozen engine calls, gated by each run's profile marker.

    No frozen source or input CSV is edited. Unmarked archived runs are exact
    pass-throughs, including when executed in the same process. Named minor
    candidate priors remain authoritative; approved offsets change only the four generic origin kernels.
    """
    from SRC import preference_engine as pe, irv, candidate_count
    if getattr(pe.diagnose_preference_weights, '_website_offset_adapter', False):
        return
    frozen_siphon = pe.apply_on_siphon
    def siphon(vec, alive, eliminated_party, seat_type, scalars):
        # v6 marker only: map current class names to the legacy keys the frozen multipliers use.
        if scalars.get(SIPHON_FIX_KEY):
            seat_type = SIPHON_CLASS_ALIASES.get(str(seat_type or "").strip().upper(), seat_type)
        return frozen_siphon(vec, alive, eliminated_party, seat_type, scalars)
    pe.apply_on_siphon = siphon
    original = _targeted(pe.diagnose_preference_weights, pe)
    signature = inspect.signature(original)
    def adapted(*args, **kwargs):
        bound = signature.bind(*args, **kwargs).arguments
        result = original(*args, **kwargs)
        flows = offset_flows(result['final_flows'], bound['eliminated_party'],
                             bound['geography_class'], bound['params'].get(OFFSET_KEY))
        flows = evidence_flows(flows, bound['eliminated_party'], bound['geography_class'],
                               bound['matrix'], bound['params'].get(EVIDENCE_KEY))
        if flows is result['final_flows']:
            return result
        return dict(result, final_flows=flows,
                    final_vector=[flows.get(p, 0.0) for p in pe.PARTIES])
    adapted._website_offset_adapter = True
    pe.diagnose_preference_weights = adapted
    irv.diagnose_preference_weights = adapted
    candidate_count.diagnose_preference_weights = adapted
