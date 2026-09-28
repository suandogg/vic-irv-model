import unittest
from unittest.mock import patch

from SRC.constants import PARTIES
from SRC.irv import (
    distribute_parcel_holder,
    initialise_parcels,
    parcel_origin_retention,
    parcel_totals,
)


def diagnostic(eliminated_party, *args, **kwargs):
    if eliminated_party == "LNP":
        return {
            "basis": "full AEC row",
            "final_flows": {"ALP": 0.2, "ON": 0.8},
            "stages": [{}],
        }
    if eliminated_party == "GRN":
        return {
            "basis": "posterior scenario",
            "final_flows": {"ALP": 0.9, "ON": 0.1},
            "stages": [{}],
        }
    raise AssertionError(eliminated_party)


class ParcelAwareIrvTests(unittest.TestCase):
    def parcels(self):
        parcels = initialise_parcels({party: 0.0 for party in PARTIES})
        parcels["LNP"]["LNP"] = 50.0
        parcels["LNP"]["GRN"] = 50.0
        return parcels

    @patch("SRC.irv.diagnose_preference_weights", side_effect=diagnostic)
    def test_full_retention_preserves_origin_and_conserves_votes(self, _):
        parcels = self.parcels()
        before = sum(parcel_totals(parcels).values())
        _, flows, origins = distribute_parcel_holder(
            parcels, "LNP", ["ALP", "ON"], {}, "Inner Ring",
            {"scalar_params": {"PARCEL_ORIGIN_RETENTION": 1.0}}, {}, {},
        )
        self.assertAlmostEqual(flows["ALP"], 0.55)
        self.assertAlmostEqual(flows["ON"], 0.45)
        self.assertEqual({row["origin"] for row in origins}, {"LNP", "GRN"})
        self.assertAlmostEqual(sum(parcel_totals(parcels).values()), before)

    @patch("SRC.irv.diagnose_preference_weights", side_effect=diagnostic)
    def test_zero_retention_reproduces_holder_only_flow(self, _):
        parcels = self.parcels()
        _, flows, _ = distribute_parcel_holder(
            parcels, "LNP", ["ALP", "ON"], {}, "Inner Ring",
            {"scalar_params": {"PARCEL_ORIGIN_RETENTION": 0.0}}, {}, {},
        )
        self.assertAlmostEqual(flows["ALP"], 0.2)
        self.assertAlmostEqual(flows["ON"], 0.8)

    @patch("SRC.irv.diagnose_preference_weights")
    def test_on_special_prior_remains_locked_for_complete_holder(self, mocked):
        mocked.return_value = {
            "basis": "ON special prior",
            "final_flows": {"ALP": 0.3, "ON": 0.7},
            "stages": [{}],
        }
        parcels = self.parcels()
        _, flows, origins = distribute_parcel_holder(
            parcels, "LNP", ["ALP", "ON"], {}, "Inner Ring",
            {"scalar_params": {"PARCEL_ORIGIN_RETENTION": 1.0}}, {}, {},
        )
        self.assertAlmostEqual(flows["ALP"], 0.3)
        self.assertAlmostEqual(flows["ON"], 0.7)
        self.assertEqual(mocked.call_count, 1)
        self.assertTrue(all(row["basis"] == "ON special prior" for row in origins))

    def test_retention_defaults_to_full_and_is_bounded(self):
        self.assertEqual(parcel_origin_retention({}), 1.0)
        self.assertEqual(parcel_origin_retention(
            {"scalar_params": {"PARCEL_ORIGIN_RETENTION": 2}}
        ), 1.0)
        self.assertEqual(parcel_origin_retention(
            {"scalar_params": {"PARCEL_ORIGIN_RETENTION": -1}}
        ), 0.0)


if __name__ == "__main__":
    unittest.main()
