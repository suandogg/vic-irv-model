import unittest

from SRC.constants import PARTIES
from SRC.preference_engine import apply_on_siphon


class OthDonorDepletionTests(unittest.TestCase):
    def setUp(self):
        self.vec = [0.40, 0.40, 0.10, 0.0, 0.10, 0.0]
        self.alive = ["ALP", "LNP", "GRN", "ON", "IND"]
        self.base = {
            "SIPHON_STRENGTH_ON": 0.25,
            "SIPHON_DONOR_CAP": 0.15,
            "OTH_ON_DONOR_DEPLETION_STRENGTH": 0.5,
            "OTH_ON_DEPLETION_BASELINE": 0.28,
            "OTH_ON_DEPLETION_REFERENCE": 24.4,
        }

    def on_share(self, scenario_on):
        scalars = {**self.base, "SCENARIO_ON_PRIMARY": scenario_on}
        result = apply_on_siphon(
            self.vec, self.alive, "OTH", "Regional", scalars
        )
        return result[PARTIES.index("ON")]

    def test_oth_to_on_siphon_declines_as_on_primary_rises(self):
        self.assertGreater(self.on_share(0.28), self.on_share(10.0))
        self.assertGreater(self.on_share(10.0), self.on_share(24.4))

    def test_moderate_setting_halves_siphon_uplift_at_reference_vote(self):
        no_siphon = apply_on_siphon(
            self.vec, self.alive, "OTH", "Regional",
            {**self.base, "SIPHON_STRENGTH_ON": 0.0},
        )[PARTIES.index("ON")]
        full = apply_on_siphon(
            self.vec, self.alive, "OTH", "Regional",
            {**self.base, "OTH_ON_DONOR_DEPLETION_STRENGTH": 0.0},
        )[PARTIES.index("ON")]
        depleted = self.on_share(24.4)
        self.assertAlmostEqual(depleted - no_siphon, (full - no_siphon) / 2)

    def test_non_oth_eliminations_are_unchanged(self):
        low = apply_on_siphon(
            self.vec, self.alive, "IND", "Regional",
            {**self.base, "SCENARIO_ON_PRIMARY": 0.28},
        )
        high = apply_on_siphon(
            self.vec, self.alive, "IND", "Regional",
            {**self.base, "SCENARIO_ON_PRIMARY": 24.4},
        )
        self.assertEqual(low, high)


if __name__ == "__main__":
    unittest.main()
