"""Native approved v6 defaults and pure flow transformations; no runtime patches."""
from copy import deepcopy
import math

ON_ALPHA = 0.8

OFFSET_CLASSES = ('Peri-urban', 'Provincial', 'Regional')

PREFERENCE_OFFSETS = {'ALP': 0.736478, 'LNP': 0.450609, 'IND': 0.745884, 'OTH': 0.98151}

EVIDENCE_OFFSETS = [{'id': 'S2-ALP+LNP',
  'donor': 'ON',
  'recipient': 'LNP',
  'classes': ['Inner Ring',
              'Middle Ring',
              'Outer Metro',
              'Peri-urban',
              'Provincial',
              'Regional'],
  'context': 'ALP+LNP',
  'offset': 0.091471,
  'seat_factor': {}},
 {'id': 'S2-ALP+GRN+LNP',
  'donor': 'ON',
  'recipient': 'LNP',
  'classes': ['Inner Ring',
              'Middle Ring',
              'Outer Metro',
              'Peri-urban',
              'Provincial',
              'Regional'],
  'context': 'ALP+GRN+LNP',
  'offset': 0.1856,
  'seat_factor': {}},
 {'id': 'S2-ALP+GRN+LNP+OTH',
  'donor': 'ON',
  'recipient': 'LNP',
  'classes': ['Inner Ring',
              'Middle Ring',
              'Outer Metro',
              'Peri-urban',
              'Provincial',
              'Regional'],
  'context': 'ALP+GRN+LNP+OTH',
  'offset': 0.013371,
  'seat_factor': {}},
 {'id': 'S2-ALP+GRN+IND+LNP',
  'donor': 'ON',
  'recipient': 'LNP',
  'classes': ['Inner Ring',
              'Middle Ring',
              'Outer Metro',
              'Peri-urban',
              'Provincial',
              'Regional'],
  'context': 'ALP+GRN+IND+LNP',
  'offset': 0.098842,
  'seat_factor': {}},
 {'id': 'C2c-ALP+GRN+LNP+ON',
  'donor': 'IND',
  'recipient': 'ON',
  'classes': ['Inner Ring', 'Middle Ring', 'Outer Metro'],
  'context': 'ALP+GRN+LNP+ON',
  'offset': -0.164,
  'seat_factor': {}},
 {'id': 'C2c-ALP+ON',
  'donor': 'IND',
  'recipient': 'ON',
  'classes': ['Inner Ring', 'Middle Ring', 'Outer Metro'],
  'context': 'ALP+ON',
  'offset': 0.5295,
  'seat_factor': {}}]

LNP_ON_TARGETS = {'donor': 'LNP',
 'recipient': 'ON',
 'multi': {'Inner Ring': 0.511139,
           'Middle Ring': 0.529125,
           'Outer Metro': 0.5013},
 'pair': {'Inner Ring': 0.63476,
          'Middle Ring': 0.63476,
          'Outer Metro': 0.63476},
 'seat_factor': {'GREENVALE': 0.0,
                 'PRESTON': 0.0,
                 'BRUNSWICK': 0.5,
                 'FOOTSCRAY': 0.5},
 'sd': 'generic'}

SPECIAL_PRIOR_OVERRIDES = {'LNP+ON|ALP|Inner Ring': {'ALP': None, 'LNP': 0.779, 'ON': 0.221},
 'LNP+ON|ALP|Middle Ring': {'ALP': None, 'LNP': 0.779, 'ON': 0.221},
 'LNP+ON|ALP|Outer Metro': {'ALP': None, 'LNP': 0.779, 'ON': 0.221}}

STATEWIDE_SD_PP = {'ALP': 2.58324923279813,
 'LNP': 2.58324923279813,
 'GRN': 1.4686042013221317,
 'ON': 2.134003178186207,
 'IND': 0.8618931878317271,
 'OTH': 0.8618931878317271}

MAJOR_RESIDUAL_FACTOR = 1.624653

INDEPENDENT_OTHER_RESIDUAL_FACTOR = 3.975

SIPHON_CLASS_ALIASES = {'INNER RING': 'INNERMETRO', 'REGIONAL': 'RURAL'}

OFFSET_KEY = '_v6_on_preference_offsets'

EVIDENCE_KEY = '_v6_evidence_offsets'

TARGET_KEY = '_v6_flow_targets'

SIPHON_FIX_KEY = 'V6_SIPHON_CLASS_NAMES'

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

def apply_defaults(params):
    from SRC.model_version import legacy_mode
    if legacy_mode(): return params
    result=deepcopy(params)
    result['_v6_defaults']=True
    from SRC.final_profile import KEY,PROFILE_ID
    result[KEY]=PROFILE_ID
    result['scalar_params']['TRIAL_VEC_EXACT_FIELD']=True
    result['scalar_params']['TRIAL_VEC_FIELD_COVERAGE']=True
    result['scalar_params']['ON alpha']=ON_ALPHA
    result[OFFSET_KEY]={'classes':list(OFFSET_CLASSES),'by_donor':dict(PREFERENCE_OFFSETS)}
    result[EVIDENCE_KEY]=deepcopy(EVIDENCE_OFFSETS)
    result[TARGET_KEY]=deepcopy(LNP_ON_TARGETS)
    result['on_special_scenario_priors'].update(deepcopy(SPECIAL_PRIOR_OVERRIDES))
    scalars=result['scalar_params']
    if 'AEC_ANCHOR_WHEN_MISSING' in scalars:scalars['AEC_ANCHOR_WHEN_MISS']=scalars['AEC_ANCHOR_WHEN_MISSING']
    scalars[SIPHON_FIX_KEY]=1.0
    from SRC.low_base_taper import load_taper_config
    from SRC.oth_scaling import load_oth_scaling_config
    result['low_base_taper']=load_taper_config()
    result['oth_scaling']=load_oth_scaling_config()
    return result
