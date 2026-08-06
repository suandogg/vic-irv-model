from pathlib import Path
import unittest

from SRC.federal_on_evidence_loader import (
    add_conservative_trial_evidence,
    conservative_reliability,
    load_federal_on_evidence,
)


ROOT = Path(__file__).resolve().parents[1]


class FederalOnEvidenceTest(unittest.TestCase):
    def test_pooled_evidence_is_on_related_and_normalised(self):
        evidence = load_federal_on_evidence(
            ROOT / "data" / "development" / "FEDERAL_VIC_ON_SCENARIOS.csv"
        )
        self.assertTrue(evidence)
        for key, scenario in evidence.items():
            eliminated, alive = key.split("|", 1)
            self.assertTrue(eliminated == "ON" or "ON" in alive.split("+"))
            self.assertAlmostEqual(sum(scenario["shares"].values()), 1.0)
            self.assertGreaterEqual(scenario["seats"], 1)
            self.assertGreater(scenario["scenario_total"], 0)
            self.assertTrue(scenario["development_only"])

    def test_conservative_trial_excludes_one_seat_scenarios(self):
        evidence = load_federal_on_evidence(
            ROOT / "data" / "development" / "FEDERAL_VIC_ON_SCENARIOS.csv"
        )
        trial = add_conservative_trial_evidence({}, evidence)
        for key, scenario in evidence.items():
            if scenario["seats"] == 1:
                self.assertNotIn(key, trial)
                self.assertEqual(conservative_reliability(scenario), 0.0)
            else:
                self.assertIn(key, trial)
                self.assertLessEqual(trial[key]["__reliability__"], 0.5)

    def test_siphon_replacement_is_explicitly_opt_in(self):
        evidence = load_federal_on_evidence(
            ROOT / "data" / "development" / "FEDERAL_VIC_ON_SCENARIOS.csv"
        )
        retained = add_conservative_trial_evidence({}, evidence)
        replaced = add_conservative_trial_evidence(
            {}, evidence, remove_on_siphon=True
        )
        key = next(iter(retained))
        self.assertFalse(retained[key]["__remove_on_siphon__"])
        self.assertTrue(replaced[key]["__remove_on_siphon__"])
