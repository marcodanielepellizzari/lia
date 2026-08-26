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
import decimal
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


def D(text):
    return decimal.Decimal(text)


class ComputeMissingPbRatiosTests(SimpleTestCase):
    """
    Only 3 of the 5 Pb ratios are independent: 207Pb/206Pb = 207Pb/204Pb /
    206Pb/204Pb, and 208Pb/206Pb = 208Pb/204Pb / 206Pb/204Pb. Given >=3 of the
    5, the rest should be derivable from these two relations -- except when
    the 3 known values are a "redundant" triple that doesn't actually pin
    down the third independent parameter (e.g. 206/204, 207/204 and the
    206/207 ratio, which is redundant with the two).
    """

    def test_fewer_than_3_known_computes_nothing(self):
        values = {"pb208_206": D("2.08"), "pb207_206": D("0.84"),
                  "pb206_204": None, "pb207_204": None, "pb208_204": None}
        resolved, computed = services.compute_missing_pb_ratios(values)
        self.assertEqual(computed, set())
        self.assertEqual(resolved, values)

    def test_three_denominator_normalized_ratios_derive_the_other_two(self):
        # The classic case from the real fixture: 206/204, 207/204, 208/204 known.
        values = {
            "pb208_206": None, "pb207_206": None,
            "pb206_204": D("18.7677"), "pb207_204": D("15.7013"), "pb208_204": D("39.0311"),
        }
        resolved, computed = services.compute_missing_pb_ratios(values)
        self.assertEqual(computed, {"pb207_206", "pb208_206"})
        self.assertEqual(resolved["pb207_206"], (D("15.7013") / D("18.7677")).quantize(D("0.000001")))
        self.assertEqual(resolved["pb208_206"], (D("39.0311") / D("18.7677")).quantize(D("0.000001")))

    def test_mixed_triple_derives_the_204_normalized_denominator(self):
        # 207/204, 207/206, 208/206 known -> 206/204 and 208/204 derivable.
        values = {
            "pb208_206": D("2.08"), "pb207_206": D("0.84"),
            "pb206_204": None, "pb207_204": D("15.7013"), "pb208_204": None,
        }
        resolved, computed = services.compute_missing_pb_ratios(values)
        self.assertEqual(computed, {"pb206_204", "pb208_204"})
        expected_x = (D("15.7013") / D("0.84")).quantize(D("0.000001"))
        self.assertEqual(resolved["pb206_204"], expected_x)
        self.assertEqual(resolved["pb208_204"], (D("2.08") * expected_x).quantize(D("0.000001")))

    def test_redundant_triple_cannot_derive_the_rest(self):
        # 206/204, 207/204 and 207/206 (== 207/204 / 206/204) carry no more
        # information than the first two alone: 208/204 and 208/206 stay unknown.
        values = {
            "pb208_206": None, "pb207_206": D("0.836660"),
            "pb206_204": D("18.7677"), "pb207_204": D("15.7013"), "pb208_204": None,
        }
        resolved, computed = services.compute_missing_pb_ratios(values)
        self.assertEqual(computed, set())
        self.assertIsNone(resolved["pb208_204"])
        self.assertIsNone(resolved["pb208_206"])

    def test_zero_denominator_does_not_crash(self):
        # 206/204 == 0 (degenerate, but shouldn't blow up): deriving 207/206
        # would require dividing by it, so it's left None instead of raising.
        values = {
            "pb208_206": D("2.08"), "pb207_206": None,
            "pb206_204": D("0"), "pb207_204": D("15.7013"), "pb208_204": None,
        }
        resolved, computed = services.compute_missing_pb_ratios(values)
        self.assertIsNone(resolved["pb207_206"])
        self.assertNotIn("pb207_206", computed)


class PreviewRowsHighlightsComputedPbRatiosTests(SimpleTestCase):
    databases = []

    def test_third_ratio_is_flagged_as_computed_in_the_preview(self):
        path = os.path.join(FIXTURES_DIR, "sample_small.csv")
        df = services.load_dataframe(path)
        # The fixture only maps 208/206, 207/206, 206/204 (3 of 5): the other
        # two should show up computed in the preview.
        column_mapping = {
            "label": "Sample Number", "country": "Country",
            "pb208_206": "208Pb/206Pb", "pb207_206": "207Pb/206Pb", "pb206_204": "206Pb/204Pb",
        }
        preview = services.preview_rows(df, column_mapping, element_columns={})
        first_row = preview["sample_rows"][0]
        self.assertTrue(first_row["computed"]["pb207_204"])
        self.assertTrue(first_row["computed"]["pb208_204"])
        self.assertFalse(first_row["computed"]["pb206_204"])
        self.assertNotEqual(first_row["vals"]["pb207_204"], "")
        self.assertNotEqual(first_row["vals"]["pb208_204"], "")
