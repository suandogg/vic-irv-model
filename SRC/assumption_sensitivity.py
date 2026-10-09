"""Frozen offline findings, not live confidence estimates or model overrides."""
FINDINGS = {
    'Bellarine': ('Generic fallback pass-through',
        'Changes the eliminated ON pile’s effective flow to ALP against LNP.', 48.6461, 50.6781),
    'Point Cook': ('Generic fallback pass-through in earlier transfers',
        'Increases earlier IND-pile transfers to ALP. The final LNP special prior stays 37% ALP / 63% ON.', 49.6998, 50.0712),
    'Pascoe Vale': ('Generic fallback pass-through',
        'Reduces the eliminated ON pile’s effective flow to ALP against GRN.', 51.1708, 49.7729),
    'Narre Warren North': ('Existing OTH depletion assumption',
        'Disabling depletion increases OTH-pile transfers to ON. The final LNP special prior stays 37% ALP / 63% ON.', 50.0800, 49.9472),
}


def finding_for_seat(seat):
    return FINDINGS.get(seat)
