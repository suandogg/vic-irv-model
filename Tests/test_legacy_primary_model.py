from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from SRC.constants import PARTIES
from SRC.legacy_primary_model import (
    apply_on_primary_donor_geography,
    apply_seat_primary_adjustments,
    build_corrected_primary_table,
    build_legacy_primary_table,
    deplete_on_primary_source_matrix,
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

    def test_party_pvi_persistence_is_configurable(self):
        current = build_corrected_primary_table(self.inputs, self.targets)
        reduced = build_corrected_primary_table(
            self.inputs, self.targets, pvi_strengths={"GRN": 0.5}
        )
        self.assertAlmostEqual(
            reduced["GRN"].mean(), current["GRN"].mean(), places=10
        )
        self.assertLess(reduced["GRN"].std(), current["GRN"].std())

    def test_zero_persistence_does_not_mutate_inputs(self):
        original = self.inputs.copy(deep=True)
        build_corrected_primary_table(
            self.inputs, self.targets, pvi_strengths={"GRN": 0.0}
        )
        pd.testing.assert_frame_equal(self.inputs, original)

    def test_on_primary_donor_strength_zero_is_identity(self):
        current = build_corrected_primary_table(self.inputs, self.targets)
        actual = apply_on_primary_donor_geography(
            self.inputs, current, self.targets,
            {seat: {"ALP": 0.2, "LNP": 0.5, "GRN": 0.02,
                    "IND": 0.05, "OTH": 0.23}
             for seat in self.inputs["seat_type"].unique()},
            strength=0.0,
        )
        pd.testing.assert_frame_equal(actual, current)

    def test_on_primary_donor_geography_preserves_targets(self):
        current = build_corrected_primary_table(self.inputs, self.targets)
        matrix = {
            seat: {"ALP": 0.2, "LNP": 0.5, "GRN": 0.02,
                   "IND": 0.05, "OTH": 0.23}
            for seat in self.inputs["seat_type"].unique()
        }
        actual = apply_on_primary_donor_geography(
            self.inputs, current, self.targets, matrix, strength=0.35
        )
        total = sum(self.targets.values())
        for party in PARTIES:
            self.assertAlmostEqual(
                actual[party].mean(), self.targets[party] / total, places=10
            )
        self.assertLess(
            (actual[PARTIES].sum(axis=1) - 1).abs().max(), 1e-12
        )

    def test_oth_depletion_conserves_source_rows(self):
        matrix = {"Outer Metro": {
            "ALP": 0.21, "LNP": 0.50, "GRN": 0.02,
            "IND": 0.05, "OTH": 0.22,
        }}
        depleted = deplete_on_primary_source_matrix(
            matrix, on_level=30, max_depletion=0.75
        )
        self.assertAlmostEqual(sum(depleted["Outer Metro"].values()), 1.0)
        self.assertAlmostEqual(depleted["Outer Metro"]["OTH"], 0.055)

    def test_retirement_and_sophomore_effects_preserve_targets(self):
        current = build_corrected_primary_table(self.inputs, self.targets)
        adjustments = pd.DataFrame([
            {
                "district": "Box Hill", "party": "ALP",
                "retiring_incumbent": True, "first_re_election": False,
                "retirement_penalty_pp": None, "sophomore_bonus_pp": None,
                "candidate_strength_pp": 0, "manual_adjustment_pp": 0,
                "enabled": True, "notes": "retirement test",
            },
            {
                "district": "Bulleen", "party": "LNP",
                "retiring_incumbent": False, "first_re_election": True,
                "retirement_penalty_pp": None, "sophomore_bonus_pp": None,
                "candidate_strength_pp": 0, "manual_adjustment_pp": 0,
                "enabled": True, "notes": "sophomore test",
            },
        ])
        actual, diagnostics = apply_seat_primary_adjustments(
            current, adjustments, self.targets,
            retirement_penalty_pp=1.0, sophomore_bonus_pp=1.0,
        )
        total = sum(self.targets.values())
        for party in PARTIES:
            self.assertAlmostEqual(
                actual[party].mean(), self.targets[party] / total, places=10
            )
        self.assertLess(
            actual.loc[actual["district"] == "Box Hill", "ALP"].iloc[0],
            current.loc[current["district"] == "Box Hill", "ALP"].iloc[0],
        )
        self.assertGreater(
            actual.loc[actual["district"] == "Bulleen", "LNP"].iloc[0],
            current.loc[current["district"] == "Bulleen", "LNP"].iloc[0],
        )
        self.assertEqual(len(diagnostics), 2)

    def test_empty_seat_adjustments_are_identity(self):
        current = build_corrected_primary_table(self.inputs, self.targets)
        actual, diagnostics = apply_seat_primary_adjustments(
            current, pd.DataFrame(), self.targets
        )
        pd.testing.assert_frame_equal(actual, current)
        self.assertTrue(diagnostics.empty)


if __name__ == "__main__":
    unittest.main()
