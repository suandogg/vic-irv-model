from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from SRC.constants import PARTIES
from SRC.legacy_primary_model import (
    build_corrected_primary_table,
    build_legacy_primary_table,
)


ROOT = Path(__file__).resolve().parents[1]


class LegacyPrimaryModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = pd.read_csv(
            ROOT / "data" / "raw" / "LEGACY_PRIMARY_INPUTS.csv"
        )
        cls.expected = pd.read_csv(
            ROOT / "tests" / "fixtures" / "LEGACY_PRIMARY_EXPECTED.csv"
        )
        cls.targets = pd.read_csv(
            ROOT / "tests" / "fixtures" / "LEGACY_PRIMARY_TARGETS.csv"
        ).iloc[0].to_dict()

    def test_matches_legacy_workbook_for_all_seats(self):
        actual = build_legacy_primary_table(self.inputs, self.targets)
        actual = actual.set_index("district")
        expected = self.expected.set_index("district")

        self.assertEqual(set(actual.index), set(expected.index))
        for party in PARTIES:
            difference = (actual[party] - expected[party]).abs().max()
            self.assertLess(
                difference,
                1e-10,
                f"{party} maximum difference was {difference}",
            )

    def test_every_district_sums_to_one(self):
        actual = build_legacy_primary_table(self.inputs, self.targets)
        differences = (actual[PARTIES].sum(axis=1) - 1).abs()
        self.assertLess(differences.max(), 1e-12)

    def test_on_index_is_normalised_before_seat_renormalisation(self):
        actual = build_legacy_primary_table(self.inputs, self.targets)
        self.assertAlmostEqual(actual["ON_index_multiplier"].mean(), 1.0)

    def test_corrected_model_hits_statewide_targets(self):
        scenarios = [
            self.targets,
            {
                "ALP": 36.66,
                "LNP": 34.48,
                "GRN": 11.50,
                "ON": 0.28,
                "IND": 5.55,
                "OTH": 11.53,
            },
            {
                "ALP": 27,
                "LNP": 27,
                "GRN": 12,
                "ON": 20,
                "IND": 7,
                "OTH": 7,
            },
        ]

        for targets in scenarios:
            actual = build_corrected_primary_table(self.inputs, targets)
            target_total = sum(targets.values())
            for party in PARTIES:
                expected = targets[party] / target_total
                self.assertAlmostEqual(actual[party].mean(), expected, places=10)
            self.assertLess(
                (actual[PARTIES].sum(axis=1) - 1).abs().max(),
                1e-12,
            )

    def test_corrected_model_supports_zero_party_target(self):
        targets = {
            "ALP": 40,
            "LNP": 40,
            "GRN": 10,
            "ON": 0,
            "IND": 5,
            "OTH": 5,
        }
        actual = build_corrected_primary_table(self.inputs, targets)
        self.assertEqual(float(actual["ON"].max()), 0.0)


if __name__ == "__main__":
    unittest.main()
