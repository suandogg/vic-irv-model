import unittest

import pandas as pd

from SRC.lnp_precollapse_loader import apply_lnp_precollapse


class TestLnpPrecollapse(unittest.TestCase):
    def setUp(self):
        self.primaries = pd.DataFrame([
            {"district": "Bass", "ALP": 30.0, "LNP": 40.0, "GRN": 10.0, "ON": 10.0, "IND": 5.0, "OTH": 5.0},
            {"district": "Ashwood", "ALP": 40.0, "LNP": 35.0, "GRN": 15.0, "ON": 5.0, "IND": 2.0, "OTH": 3.0},
        ])

    @staticmethod
    def inputs(strength=1.0, enabled=True, override=None):
        return pd.DataFrame([
            {"ElectorateKey": "BASS", "DestinationCategory": "ALP", "Share": 0.10, "Enabled": enabled, "Strength": strength, "ManualOverrideShare": override},
            {"ElectorateKey": "BASS", "DestinationCategory": "LNP", "Share": 0.90, "Enabled": enabled, "Strength": strength, "ManualOverrideShare": None if override is None else 1.0 - override},
        ])

    def test_full_strength_moves_only_configured_seat(self):
        result = apply_lnp_precollapse(self.primaries, self.inputs())
        bass = result[result["district"] == "Bass"].iloc[0]
        self.assertAlmostEqual(bass["ALP"], 34.0)
        self.assertAlmostEqual(bass["LNP"], 36.0)
        pd.testing.assert_series_equal(result.iloc[1], self.primaries.iloc[1])

    def test_partial_strength_blends_with_original_lnp(self):
        result = apply_lnp_precollapse(self.primaries, self.inputs(strength=0.5))
        bass = result[result["district"] == "Bass"].iloc[0]
        self.assertAlmostEqual(bass["ALP"], 32.0)
        self.assertAlmostEqual(bass["LNP"], 38.0)

    def test_disabled_input_has_no_effect(self):
        pd.testing.assert_frame_equal(
            apply_lnp_precollapse(self.primaries, self.inputs(enabled=False)),
            self.primaries,
        )

    def test_manual_override_replaces_empirical_share(self):
        result = apply_lnp_precollapse(self.primaries, self.inputs(override=0.20))
        bass = result[result["district"] == "Bass"].iloc[0]
        self.assertAlmostEqual(bass["ALP"], 38.0)
        self.assertAlmostEqual(bass["LNP"], 32.0)

    def test_vote_total_is_conserved(self):
        result = apply_lnp_precollapse(self.primaries, self.inputs())
        columns = ["ALP", "LNP", "GRN", "ON", "IND", "OTH"]
        pd.testing.assert_series_equal(result[columns].sum(axis=1), self.primaries[columns].sum(axis=1))

    def test_csv_style_nan_override_uses_empirical_share(self):
        inputs = self.inputs()
        inputs["ManualOverrideShare"] = float("nan")
        result = apply_lnp_precollapse(self.primaries, inputs)
        bass = result[result["district"] == "Bass"].iloc[0]
        self.assertAlmostEqual(bass["ALP"], 34.0)
        self.assertAlmostEqual(bass["LNP"], 36.0)


if __name__ == "__main__":
    unittest.main()
