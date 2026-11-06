import unittest
from streamlit.testing.v1 import AppTest


class FieldSwitchTests(unittest.TestCase):
    def test_switch_changes_central_count_and_reverts(self):
        app = AppTest.from_file('app.py', default_timeout=120).run()
        self.assertEqual(len(app.exception), 0)
        self.assertFalse(app.checkbox(key='candidate_field_version_b').value)
        app.checkbox(key='candidate_field_version_b').check().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        app.checkbox(key='candidate_field_version_b').uncheck().run()
        self.assertEqual(len(app.exception), 0)
