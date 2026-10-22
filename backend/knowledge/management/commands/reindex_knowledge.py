from django.core.management.base import BaseCommand, CommandError

from knowledge.services import chunk_service
from workspaces.models import Workspace


class Command(BaseCommand):
    help = (
        "Re-split every article into search passages and rebuild their search vectors."
    )

    def add_arguments(self, parser):
        parser.add_argument("--workspace", help="Only this workspace (its slug).")
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
