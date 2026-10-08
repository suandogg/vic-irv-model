"""Guard the laboratory deployment against inherited reference sheet settings."""
import os
import unittest
from unittest.mock import patch
from SRC.live_sheet_sync import DEFAULT_SHEET_ID, resolve_sheet_id

TEST_SHEET_ID = "1sLmANVOERsbV08BIZYUfT_fccTGw-mCvAwJSAD_4968"
REFERENCE_SHEET_ID = "1avkQZ0A8tlVI1tR0UakEriNKuq9N7dwRUFJzecb26Ro"


class TestingSheetIsolation(unittest.TestCase):
    def test_laboratory_default(self):
        self.assertEqual(DEFAULT_SHEET_ID, TEST_SHEET_ID)

    def test_entrypoint_environment_overrides_old_secrets(self):
        with patch.dict(os.environ, {"VIC_IRV_SHEET_ID": TEST_SHEET_ID}):
            self.assertEqual(resolve_sheet_id({"VIC_IRV_SHEET_ID": REFERENCE_SHEET_ID}), TEST_SHEET_ID)


if __name__ == "__main__":
    unittest.main()
