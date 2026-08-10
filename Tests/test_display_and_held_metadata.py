from __future__ import annotations

import unittest

import pandas as pd

from SRC.display_metrics import held_party_2cp_swing
from SRC.loaders import apply_seat_held_metadata, load_seat_held_metadata


class HeldMetadataTest(unittest.TestCase):
    def test_seat_helper_is_authoritative_for_ringwood(self):
        metadata = load_seat_held_metadata()
        self.assertEqual(
            metadata.set_index("district").loc["Ringwood", "held_by"],
            "ALP",
        )

    def test_overlay_changes_only_held_party(self):
        inputs = pd.DataFrame([
            {"district": "Ringwood", "held_by": "LNP", "ALP_pvi": 0.1}
        ])
        metadata = pd.DataFrame([
            {"district": "Ringwood", "held_by": "ALP"}
        ])
        result = apply_seat_held_metadata(inputs, metadata)
        self.assertEqual(result.loc[0, "held_by"], "ALP")
        self.assertEqual(result.loc[0, "ALP_pvi"], 0.1)


class HeldPartySwingTest(unittest.TestCase):
    def setUp(self):
        self.baseline = pd.DataFrame([
            {"district": "Bayswater", "ALP_2CP": 0.5423, "LNP_2CP": 0.4577},
        ]).set_index("district")

    def test_loss_is_negative_from_held_party_perspective(self):
        row = {
            "district": "Bayswater", "held_by": "ALP",
            "winner": "ON", "runner_up": "ALP",
            "winner_pct": 0.5001, "runner_up_pct": 0.4999,
        }
        self.assertAlmostEqual(held_party_2cp_swing(row, self.baseline), -4.24)

    def test_held_party_gain_is_positive(self):
        row = {
            "district": "Bayswater", "held_by": "ALP",
            "winner": "ALP", "runner_up": "ON",
            "winner_pct": 0.60, "runner_up_pct": 0.40,
        }
        self.assertAlmostEqual(held_party_2cp_swing(row, self.baseline), 5.77)

    def test_blank_when_held_party_misses_final_two(self):
        row = {
            "district": "Bayswater", "held_by": "ALP",
            "winner": "ON", "runner_up": "LNP",
            "winner_pct": 0.51, "runner_up_pct": 0.49,
        }
        self.assertIsNone(held_party_2cp_swing(row, self.baseline))


if __name__ == "__main__":
    unittest.main()
