import unittest
import pandas as pd
from SRC.trial_seat_panel import comparison_panel, SEATS
from SRC.matrix_loader import load_synth_pref_matrices
from pathlib import Path

class PanelTests(unittest.TestCase):
    def test_every_scenario_and_variant_has_five_seats(self):
        root=Path(__file__).resolve().parents[1]
        results=pd.read_csv(root/"reports/preference_review_2026_10_08/seat_results.csv")
        matrices=load_synth_pref_matrices()
        for scenario,method in results[["Scenario","Variant"]].drop_duplicates().itertuples(index=False,name=None):
            rows=comparison_panel(results,scenario,method,matrices)
            self.assertEqual([r["Seat"] for r in rows],SEATS)
            if method=="reference":
                self.assertTrue(all(abs(r["ALP forced 2PP change (pp)"])<1e-10 for r in rows))
                self.assertTrue(all(not r["Elimination order changed"] for r in rows))

if __name__=="__main__": unittest.main()
