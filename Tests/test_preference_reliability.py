import unittest

from SRC.irv import preference_source_category


class PreferenceReliabilityTest(unittest.TestCase):
    def test_user_facing_categories(self):
        self.assertEqual(
            preference_source_category("federal ON evidence trial"),
            "Exact federal evidence",
        )
        for basis in ["full AEC row", "partial AEC row", "posterior scenario"]:
            self.assertEqual(
                preference_source_category(basis),
                "Victorian preference evidence",
            )
        self.assertEqual(
            preference_source_category("ON special prior"), "Special prior"
        )
        for basis in ["matrix", "ideology prior", "uniform fallback"]:
            self.assertEqual(
                preference_source_category(basis), "Generic matrix or fallback"
            )


if __name__ == "__main__":
    unittest.main()
