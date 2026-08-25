"""
Command-line import, for bulk/batch loading (e.g. the initial import of
the historical archive) without going through the web wizard.
Uses the same logic as datasets.services, shared with the web pages.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from datasets import services
from workflow.models import Dataset, DatasetVisibility, DatasetStatus, MergeRequest


class Command(BaseCommand):
    help = "Imports a CSV/sheet in the 'Database ores' format into a private dataset."

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str)
        parser.add_argument("--owner", required=True, help="username of the dataset owner")
        parser.add_argument("--dataset-name", required=True)
        parser.add_argument("--visibility", default="private", choices=["private", "shared"])
        parser.add_argument("--submit-for-review", action="store_true")

    def handle(self, *args, **options):
        owner = User.objects.filter(username=options["owner"]).first()
        if not owner:
            raise CommandError(f"User '{options['owner']}' not found.")

        df = services.load_dataframe(options["file_path"])
        column_mapping = services.guess_mapping(df.columns)
        element_columns = services.detect_trace_element_columns(df.columns)

        missing_required = [
            label for key, label, required in services.FIELD_DEFINITIONS
            if required and not column_mapping.get(key)
        ]
        if missing_required:
            raise CommandError(
                f"Could not guess the column for required fields: {missing_required}. "
                "Use the web wizard for manual mapping."
            )

        with transaction.atomic():
            dataset = Dataset.objects.create(
                name=options["dataset_name"],
                owner=owner,
                visibility=DatasetVisibility.SHARED if options["visibility"] == "shared" else DatasetVisibility.PRIVATE,
                status=DatasetStatus.DRAFT,
                source_file_name=options["file_path"],
            )
            created_count, new_anag = services.import_rows(df, dataset, owner, column_mapping, element_columns)

            merge_request = None
            if options["submit_for_review"]:
                merge_request = MergeRequest.objects.create(
                    dataset=dataset, submitted_by=owner, new_anagraphical_values=new_anag,
                )
                dataset.status = DatasetStatus.PENDING_REVIEW
                dataset.save(update_fields=["status"])

        self.stdout.write(self.style.SUCCESS(
            f"Imported {created_count} samples into dataset '{dataset.name}' (id={dataset.id})."
        ))
        if merge_request:
            self.stdout.write(self.style.SUCCESS(f"Merge request #{merge_request.id} created for review."))
        for kind, values in new_anag.items():
            if values:
                self.stdout.write(f"  New anagraphical values ({kind}): {sorted(set(values))}")
