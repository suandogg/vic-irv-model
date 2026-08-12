import unittest

from SRC.constants import PARTIES
from SRC.preference_engine import apply_geo_adjust


class NonOnGeographyStrengthTests(unittest.TestCase):
    def setUp(self):
        self.vec = [0.25, 0.25, 0.15, 0.15, 0.10, 0.10]
        self.alive = list(PARTIES)
        self.params = {
            "geography_adjustments": {
                "Rural": {
                    "ALP": -0.06, "LNP": 0.06, "GRN": -0.10,
                    "ON": 0.10, "IND": 0.02, "OTH": 0.0,
                }
            },
            "scalar_params": {},
        }

    def test_default_retains_full_existing_adjustment(self):
        default = apply_geo_adjust(self.vec, self.alive, "Regional", self.params, "OTH")
        explicit = apply_geo_adjust(
            self.vec, self.alive, "Regional",
            {**self.params, "scalar_params": {"NON_ON_GEOGRAPHY_STRENGTH": 1}},
            "OTH",
        )
        self.assertEqual(default, explicit)

    def test_three_quarters_scales_only_non_on_adjustments(self):
        actual = apply_geo_adjust(
            self.vec, self.alive, "Regional",
            {**self.params, "scalar_params": {"NON_ON_GEOGRAPHY_STRENGTH": 0.75}},
            "OTH",
        )
        raw = [0.205, 0.295, 0.075, 0.25, 0.115, 0.10]
        expected = [value / sum(raw) for value in raw]
        for observed, wanted in zip(actual, expected):
            self.assertAlmostEqual(observed, wanted)


if __name__ == "__main__":
    unittest.main()
