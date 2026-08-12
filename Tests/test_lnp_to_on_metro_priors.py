import unittest

from SRC.params_loader import load_params


class LnpToOnMetroPriorTests(unittest.TestCase):
    def test_approved_final_two_priors_load_exactly(self):
        priors = load_params()["on_special_scenario_priors"]
        expected = {
            "ALP+ON|LNP|Inner Ring": {"ALP": 0.50, "ON": 0.50},
            "ALP+ON|LNP|Middle Ring": {"ALP": 0.44, "ON": 0.56},
            "ALP+ON|LNP|Outer Metro": {"ALP": 0.37, "ON": 0.63},
        }
        for key, shares in expected.items():
            self.assertAlmostEqual(priors[key]["ALP"], shares["ALP"])
            self.assertAlmostEqual(priors[key]["ON"], shares["ON"])
            self.assertIsNone(priors[key]["LNP"])


if __name__ == "__main__":
    unittest.main()
