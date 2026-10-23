from django.core.management.base import BaseCommand, CommandError

from knowledge.constants.enums import UploadStatus
from knowledge.models import KnowledgeUpload
from knowledge.services import chunk_service
from knowledge.tasks import index_upload
from workspaces.models import Workspace


class Command(BaseCommand):
    help = (
        "Re-split every article into search passages and rebuild their search vectors. "
        "With --uploads, also queue every confirmed upload to be read again."
    )

    def add_arguments(self, parser):
        parser.add_argument("--workspace", help="Only this workspace (its slug).")
        parser.add_argument(
            "--uploads",
            action="store_true",
            help="Also queue all confirmed uploads for re-reading (the documents worker does the work).",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Count articles, write nothing."
        )

    def handle(self, *args, **options):
        workspace_id = None
        if options["workspace"]:
            workspace = Workspace.all_objects.filter(slug=options["workspace"]).first()
            if workspace is None:
                raise CommandError(f"No workspace with slug {options['workspace']!r}.")
            workspace_id = workspace.id
        articles, chunks = chunk_service.reindex_articles(
            workspace_id, dry_run=options["dry_run"]
        )
        if options["dry_run"]:
            self.stdout.write(f"would rebuild {articles} articles")
        else:
            self.stdout.write(f"reindexed {articles} articles, {chunks} chunks")
        if options["uploads"]:
            uploads = KnowledgeUpload.objects.filter(status=UploadStatus.READY)
            if workspace_id is not None:
                uploads = uploads.filter(workspace_id=workspace_id)
            ids = list(uploads.values_list("id", flat=True))
            if options["dry_run"]:
                self.stdout.write(f"would queue {len(ids)} uploads")
            else:
                for upload_id in ids:
                    index_upload.delay(str(upload_id), force=True)
                self.stdout.write(f"queued {len(ids)} uploads")
