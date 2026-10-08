import pandas as pd

from SRC.turnout_loader import attach_turnout_weights, turnout_weighted_share


def test_turnout_weighted_share_differs_from_seat_mean():
    results = pd.DataFrame({
        "district": ["A", "B"],
        "ALP_2PP": [0.40, 0.60],
    })
    weights = pd.DataFrame({
        "district": ["A", "B"],
        "formal_votes_2022": [1, 3],
    })
    attached = attach_turnout_weights(results, weights)
    assert turnout_weighted_share(attached, "ALP_2PP") == 0.55
