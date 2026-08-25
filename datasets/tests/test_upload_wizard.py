"""
End-to-end regression test for the upload wizard (upload -> map columns ->
preview -> import), covering the exact path the user hit the reported bug
on: uploading a legacy .xls file 500s at the "map columns" step because
services.load_dataframe() needs the `xlrd` package.

Runs the same flow for .csv, .xlsx and .xls so the fix is proven against
the wizard views themselves, not just the pandas call site.
"""
import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from datasets.models import Sample
from workflow.models import Dataset, DatasetStatus, DatasetVisibility

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

# Column mapping shared by all three fixtures: they're the same 10 rows,
# just saved in different formats.
COLUMN_MAPPING = {
    "map__label": "Sample Number",
    "map__country": "Country",
    "map__region": "Region",
    "map__pb208_206": "208Pb/206Pb",
    "map__pb207_206": "207Pb/206Pb",
    "map__pb206_204": "206Pb/204Pb",
}


class UploadWizardTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="uploader", password="pw12345")
        self.client.login(username="uploader", password="pw12345")

    def _run_wizard(self, fixture_filename):
        dataset = Dataset.objects.create(
            name=f"Wizard test - {fixture_filename}",
            owner=self.user,
            visibility=DatasetVisibility.PRIVATE,
            status=DatasetStatus.DRAFT,
        )

        with override_settings(MEDIA_ROOT=self.media_root):
            fixture_path = os.path.join(FIXTURES_DIR, fixture_filename)
            with open(fixture_path, "rb") as fh:
                response = self.client.post(
                    reverse("dataset-upload", args=[dataset.pk]),
                    {"file": fh},
                )
            self.assertRedirects(response, reverse("dataset-upload-map", args=[dataset.pk]))

            # This is the step that 500s today for .xls without the xlrd fix.
            response = self.client.get(reverse("dataset-upload-map", args=[dataset.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertIn("Sample Number", response.context["detected_columns"])

            response = self.client.post(
                reverse("dataset-upload-map", args=[dataset.pk]), COLUMN_MAPPING
            )
            self.assertRedirects(response, reverse("dataset-upload-preview", args=[dataset.pk]))

            response = self.client.get(reverse("dataset-upload-preview", args=[dataset.pk]))
            self.assertEqual(response.status_code, 200)

            response = self.client.post(reverse("dataset-upload-preview", args=[dataset.pk]))
            self.assertRedirects(response, reverse("dataset-detail", args=[dataset.pk]))

        self.assertEqual(Sample.objects.filter(dataset=dataset).count(), 10)

    def test_wizard_with_csv(self):
        self._run_wizard("sample_small.csv")

    def test_wizard_with_xlsx(self):
        self._run_wizard("sample_small.xlsx")

    def test_wizard_with_xls(self):
        self._run_wizard("sample_small.xls")
