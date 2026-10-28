import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
from streamlit.testing.v1 import AppTest
from SRC import live_sheet_sync as sync


class SyncDiagnosticsTests(unittest.TestCase):
    def test_safe_errors_do_not_echo_payloads(self):
        secret='private_key=do-not-display'
        exc=RuntimeError(secret)
        self.assertNotIn(secret,sync.safe_sync_error(exc))
        exc.response=SimpleNamespace(status_code=429)
        self.assertIn('429',sync.safe_sync_error(exc))
        self.assertNotIn(secret,sync.safe_sync_error(exc))
        self.assertIn('Duplicate',sync.safe_sync_error(RuntimeError('headers are not unique')))

    def test_per_tab_failure_and_saved_file_reporting(self):
        import pandas as pd
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'bad.csv').write_text('a\n1\n')
            book=Mock()
            book.worksheets.return_value=[SimpleNamespace(title=x) for x in ['Good','Bad','Empty']]
            book.worksheet.side_effect=lambda name: name
            def read(name,_):
                if name=='Bad':
                    raise RuntimeError('headers are not unique')
                return pd.DataFrame({'a':[1]}) if name=='Good' else pd.DataFrame()
            with patch.object(sync,'DATA_DIR',Path(folder)),patch.object(sync,'FILES',{
                    'Good':'good.csv','Bad':'bad.csv','Empty':'empty.csv','Missing':'missing.csv'}),\
                 patch.object(sync,'resolve_credentials',return_value=object()),\
                 patch.object(sync.gspread,'authorize') as auth,\
                 patch.object(sync,'worksheet_to_dataframe',side_effect=read):
                auth.return_value.open_by_key.return_value=book
                result=sync.sync_inputs_from_google_sheet()
            self.assertEqual(result['synced'],1)
            rows={r['tab']:r for r in result['diagnostics']}
            self.assertEqual(rows['Bad']['status'],'error')
            self.assertTrue(rows['Bad']['saved_csv_available'])
            self.assertFalse(rows['Missing']['saved_csv_available'])
            self.assertEqual(rows['Empty']['status'],'skipped')
            self.assertEqual(Path(folder,'bad.csv').read_text(),'a\n1\n')

    def test_ui_shows_failure_and_fallback(self):
        app=AppTest.from_string('''
from SRC.sync_status_ui import render_sync_diagnostics
render_sync_diagnostics({'synced':32,'errors':['not rendered'], 'diagnostics':[
{'tab':'Example tab','status':'error','reason':'Google read-request quota/rate limit reached (HTTP 429).',
 'file':'example.csv','saved_csv_available':True,'saved_csv_modified_utc':'2026-10-29'},
{'tab':'Missing tab','status':'skipped','reason':'Tab not found in workbook.',
 'file':'missing.csv','saved_csv_available':False}]})
''').run()
        self.assertEqual(len(app.exception),0)
        self.assertIn('Example tab',app.warning[0].value)
        self.assertTrue(any('429' in x.value for x in app.text))
        self.assertTrue(any('Retaining saved input' in x.value for x in app.caption))
        self.assertTrue(any('No nonempty saved CSV' in x.value for x in app.error))


if __name__=='__main__':
    unittest.main()
