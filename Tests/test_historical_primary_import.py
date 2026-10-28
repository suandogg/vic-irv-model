import importlib.util
from pathlib import Path
import unittest


@unittest.skipUnless(importlib.util.find_spec('lxml'),'Historical importer uses bundled lxml')
class HistoricalPrimaryImportTests(unittest.TestCase):
    def test_official_category_labels_preserved(self):
        from tools.assemble_historical_primaries import category
        expected={'LIBERAL':'LNP','THE NATIONALS':'LNP','LIBERAL DEMOCRATS':'OTH',
                  'AUSTRALIAN LABOR PARTY':'ALP','AUSTRALIAN GREENS':'GRN',
                  '':'IND',"PAULINE HANSON'S ONE NATION":'ON'}
        for label,value in expected.items():
            self.assertEqual(category(label),value)

    def test_primary_table_selected_not_final_pair(self):
        from tools.assemble_historical_primaries import parse_district
        page=b'''<h2>Example District</h2><table><tr><th>Formal Votes:</th><td>100</td></tr></table>
        <table title="First preference votes"><tr><th>Candidate</th></tr>
        <tr><td>A</td><td>LIBERAL</td><td>60</td><td>60.00%</td></tr>
        <tr><td>B</td><td>AUSTRALIAN LABOR PARTY</td><td>40</td><td>40.00%</td></tr></table>
        <table title="Two candidate preferred"><tr><td>A</td><td>LIBERAL</td><td>70</td><td>70%</td></tr></table>'''
        rows=parse_district(page,2014,'https://official.example')
        self.assertEqual([r['Votes'] for r in rows],[60,40])
        self.assertEqual(rows[0]['District'],'Example')
        self.assertEqual(rows[0]['SourceURL'],'https://official.example')
        with self.assertRaises(ValueError):
            parse_district(page.replace(b'<td>40</td>',b'<td>39</td>'),2014,'test')
        with self.assertRaises(ValueError):
            parse_district(page.replace(b'60.00%',b'61.00%'),2014,'test')

    def test_cached_full_panel_controls(self):
        import pandas as pd
        root=Path(__file__).resolve().parents[1]/'data/research/historical_primaries_2026_10_29'
        if not (root/'candidates.csv').exists():
            self.skipTest('Historical source panel not assembled')
        raw=pd.read_csv(root/'candidates.csv')
        panel=pd.read_csv(root/'district_primaries.csv')
        self.assertEqual(raw.groupby('Year').District.nunique().to_dict(),{2014:88,2018:88})
        self.assertEqual(raw.groupby('Year').Votes.sum().to_dict(),{2014:3355707,2018:3514474})
        self.assertFalse(raw.duplicated(['Year','District','Candidate']).any())
        self.assertFalse(panel.duplicated(['Year','District']).any())
        totals=panel[['ALP','LNP','GRN','ON','IND','OTH']].sum(axis=1)
        self.assertTrue((abs(totals-1)<1e-12).all())


if __name__=='__main__':
    unittest.main()
