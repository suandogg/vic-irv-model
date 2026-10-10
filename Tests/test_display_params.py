import csv
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from SRC.display_params import SPECS, defaults, load_display_params, parameter_rows, validate_one
from SRC.presentation import effective, party_summary


class DisplayTests(unittest.TestCase):
    def test_committed_settings_match_defaults(self):
        actual,warnings = load_display_params()
        self.assertEqual(warnings,[])
        self.assertEqual(actual,defaults())
        self.assertEqual(len(SPECS),len(defaults()))

    def test_every_default_valid(self):
        for spec in SPECS:
            self.assertEqual(validate_one(spec,spec['Default']),spec['Default'],spec['Parameter'])

    def test_invalid_values_safe_and_warn(self):
        rows = parameter_rows()
        bad = {'BACKGROUND':'red; } <script>','APP_TITLE':'','METRIC_FONT_PX':'NaN',
               'CARD_SHADOW':'yes','PARTY_ORDER':'ALP,ALP','NAV_FORECAST':'Dashboard'}
        for row in rows[1:]:
            if row[1] in bad: row[2]=bad[row[1]]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'display.csv'
            with path.open('w',newline='') as handle: csv.writer(handle).writerows(rows)
            settings,warnings=load_display_params(path)
        self.assertGreaterEqual(len(warnings),6)
        for key in bad: self.assertEqual(settings[key],defaults()[key])

    def test_labels_and_order_do_not_mutate_results(self):
        frame=pd.DataFrame({'Party':['ALP','LNP'],'Seats':[30,40]})
        snapshot=frame.copy(deep=True)
        settings=defaults()|{'ALP_LABEL':'Labor test'}
        output=party_summary(frame,settings)
        self.assertEqual(output.Party.tolist(),['Coalition','Labor test'])
        self.assertEqual(output.Seats.tolist(),[40,30])
        pd.testing.assert_frame_equal(frame,snapshot)
        self.assertEqual(effective(settings|{'THEME':'dark'})['BACKGROUND'],'#101318')

    def test_sync_and_engine_separation(self):
        from SRC.live_sheet_sync import FILES
        self.assertEqual(FILES['DISPLAY PARAMS'],'DISPLAY PARAMS.csv')
        root=Path(__file__).resolve().parents[1]/'SRC'
        for name in ('forecast_engine.py','primary_pipeline.py','irv.py','preference_engine.py'):
            self.assertNotIn('display_params',(root/name).read_text())


if __name__=='__main__': unittest.main()
