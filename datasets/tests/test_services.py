"""
Regression tests for datasets/services.py's file-reading step.

Fixtures under datasets/tests/fixtures/ are a 10-row extract of the first
sheet of a real "Isotrace" dataset file the user uploads in practice, saved
as .csv, .xlsx and .xls so all three formats accepted by the upload wizard
(datasets/forms.py's UploadFileForm: .csv, .xls, .xlsx) are exercised.

The .xls case is the direct regression test for the reported bug: reading
legacy .xls needs the `xlrd` package, which was missing from requirements.txt
(openpyxl only covers .xlsx/.xlsm) and made load_dataframe() raise ImportError.
"""
import os

from django.test import SimpleTestCase

from datasets import services

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

EXPECTED_COLUMNS = [
    "Sample Number", "Country", "Region", "Deposit", "Mine",
    "Type", "Main constituent", "Description",
    "208Pb/206Pb", "207Pb/206Pb", "206Pb/204Pb",
]


class LoadDataframeTests(SimpleTestCase):
    databases = []

    def _assert_loads_fixture(self, filename):
        path = os.path.join(FIXTURES_DIR, filename)
        df = services.load_dataframe(path)
        self.assertEqual(len(df), 10)
        self.assertEqual(list(df.columns), EXPECTED_COLUMNS)
        self.assertEqual(df.iloc[0]["Sample Number"], "JS7/1")
        self.assertEqual(df.iloc[0]["Country"], "Italy")

    def test_load_csv(self):
        self._assert_loads_fixture("sample_small.csv")

    def test_load_xlsx(self):
        self._assert_loads_fixture("sample_small.xlsx")

    def test_load_xls(self):
        """Legacy .xls: fails with ImportError if xlrd isn't installed."""
        self._assert_loads_fixture("sample_small.xls")


class GuessMappingTests(SimpleTestCase):
    databases = []

    def test_guesses_label_and_country_from_real_headers(self):
        guessed = services.guess_mapping(EXPECTED_COLUMNS)
        self.assertEqual(guessed["country"], "Country")
