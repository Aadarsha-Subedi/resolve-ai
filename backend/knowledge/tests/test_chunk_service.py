from io import StringIO
from unittest import mock, skipUnless

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

from knowledge.models import KnowledgeArticle, KnowledgeChunk
from knowledge.tests.base import KnowledgeTestCase

POSTGRES = connection.vendor == "postgresql"

BODY = (
    "Welcome.\n\n# Invoices\nInvoices arrive monthly.\n\n"
    "# Refunds\nRefunds take five days.\n\n## Annual plans\nAnnual plans refund in 14 days."
)


class LanguageChangeMixin:
    def set_language(self, language):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.owner_client.patch(
                f"/api/workspaces/{self.workspace_id}/",
                {"search_language": language},
                format="json",
            )
        self.assertEqual(response.status_code, 200)


class ChunkSyncTests(LanguageChangeMixin, KnowledgeTestCase):
    def article(self, title="Billing", content=BODY):
        return self.create_article(title=title, content=content)

    def chunks(self, article_id):
        return list(KnowledgeChunk.objects.filter(article_id=article_id))

    def test_create_writes_chunks_in_order(self):
        data = self.article()
        chunks = self.chunks(data["id"])
        self.assertEqual(
            [(c.position, c.heading_path) for c in chunks],
            [
                (0, "Billing"),
                (1, "Billing > Invoices"),
                (2, "Billing > Refunds"),
                (3, "Billing > Refunds > Annual plans"),
            ],
        )
        self.assertEqual({c.search_language for c in chunks}, {"english"})
        self.assertEqual({str(c.workspace_id) for c in chunks}, {self.workspace_id})

    def test_empty_article_has_no_chunks_until_it_gets_content(self):
        data = self.article(content="")
        self.assertEqual(self.chunks(data["id"]), [])
        self.owner_client.patch(
            self.kurl(f"articles/{data['id']}/"),
            {"content": "Now text."},
            format="json",
        )
        self.assertEqual([c.text for c in self.chunks(data["id"])], ["Now text."])

    def test_editing_content_replaces_the_chunks(self):
        data = self.article()
        before = {c.id for c in self.chunks(data["id"])}
        self.owner_client.patch(
            self.kurl(f"articles/{data['id']}/"),
            {"content": "# Shipping\nShips in two days."},
            format="json",
        )
        after = self.chunks(data["id"])
        self.assertEqual([c.heading_path for c in after], ["Billing > Shipping"])
        self.assertTrue(before.isdisjoint({c.id for c in after}))

    def test_editing_the_title_updates_the_heading_paths(self):
        data = self.article()
        self.owner_client.patch(
            self.kurl(f"articles/{data['id']}/"), {"title": "Payments"}, format="json"
        )
        paths = [c.heading_path for c in self.chunks(data["id"])]
        self.assertTrue(all(p.startswith("Payments") for p in paths), paths)

    def test_categories_only_edit_and_same_values_keep_the_chunks(self):
        data = self.article()
        before = [c.id for c in self.chunks(data["id"])]
        url = self.kurl(f"articles/{data['id']}/")
        self.owner_client.patch(
            url, {"category_ids": [self.category_id("FAQ")]}, format="json"
        )
        self.owner_client.patch(
            url, {"title": "Billing", "content": BODY}, format="json"
        )
        self.assertEqual([c.id for c in self.chunks(data["id"])], before)

    def test_status_changes_keep_the_chunks(self):
        data = self.article()
        before = [c.id for c in self.chunks(data["id"])]
        for action in ("publish", "unpublish", "archive"):
            response = self.owner_client.post(
                self.kurl(f"articles/{data['id']}/{action}/")
            )
            self.assertEqual(response.status_code, 200, action)
            self.assertEqual([c.id for c in self.chunks(data["id"])], before, action)

    def test_deleting_the_article_removes_its_chunks(self):
        data = self.article()
        self.owner_client.delete(self.kurl(f"articles/{data['id']}/"))
        self.assertEqual(KnowledgeChunk.objects.count(), 0)

    def test_a_failure_while_chunking_undoes_the_article(self):
        with (
            mock.patch(
                "knowledge.services.article_service.chunk_service.rebuild_chunks",
                side_effect=RuntimeError("boom"),
            ),
            self.assertRaises(RuntimeError),
        ):
            self.article()
        self.assertEqual(KnowledgeArticle.objects.count(), 0)
        self.assertEqual(self.used(), 0)

    def test_other_workspaces_are_untouched_by_a_language_change(self):
        mine = self.article()
        other_ws = self.create_workspace(name="Other")["id"]
        self.owner_client.post(
            self.kurl("articles/", workspace_id=other_ws),
            {"title": "Other", "content": "Some text."},
            format="json",
        )
        self.set_language("spanish")
        self.assertEqual(
            {c.search_language for c in self.chunks(mine["id"])}, {"spanish"}
        )
        self.assertEqual(
            set(
                KnowledgeChunk.objects.filter(workspace_id=other_ws).values_list(
                    "search_language", flat=True
                )
            ),
            {"english"},
        )

    def test_new_articles_use_the_workspace_language(self):
        self.set_language("german")
        data = self.article()
        self.assertEqual(
            {c.search_language for c in self.chunks(data["id"])}, {"german"}
        )


class ReindexCommandTests(KnowledgeTestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command("reindex_knowledge", *args, stdout=out)
        return out.getvalue().strip()

    def test_dry_run_counts_and_writes_nothing(self):
        data = self.create_article(content=BODY)
        KnowledgeChunk.objects.all().delete()
        self.assertEqual(self.run_command("--dry-run"), "would rebuild 1 articles")
        self.assertEqual(
            KnowledgeChunk.objects.filter(article_id=data["id"]).count(), 0
        )

    def test_reindex_rebuilds_missing_chunks(self):
        data = self.create_article(content=BODY)
        KnowledgeChunk.objects.all().delete()
        self.assertEqual(self.run_command(), "reindexed 1 articles, 4 chunks")
        self.assertEqual(
            KnowledgeChunk.objects.filter(article_id=data["id"]).count(), 4
        )

    def test_reindex_one_workspace_by_slug(self):
        self.create_article(content=BODY)
        other = self.create_workspace(name="Other")
        self.owner_client.post(
            self.kurl("articles/", workspace_id=other["id"]),
            {"title": "T", "content": "x"},
            format="json",
        )
        KnowledgeChunk.objects.all().delete()
        self.assertEqual(
            self.run_command("--workspace", other["slug"]),
            "reindexed 1 articles, 1 chunks",
        )

    def test_unknown_workspace_is_an_error(self):
        with self.assertRaises(CommandError):
            self.run_command("--workspace", "nope")


@skipUnless(POSTGRES, "needs Postgres full-text search")
class ChunkVectorTests(LanguageChangeMixin, KnowledgeTestCase):
    def found(self, q, config="english"):
        from common.search.query import search

        qs = search(
            KnowledgeChunk.objects.all(),
            q,
            config=config,
            vector_field="search_vector",
        )
        return sorted(c.heading_path for c in qs)

    def test_vectors_are_filled_and_stemmed(self):
        self.create_article(title="Billing", content=BODY)
        self.assertFalse(
            KnowledgeChunk.objects.filter(search_vector__isnull=True).exists()
        )
        self.assertEqual(
            self.found("refunded"),
            ["Billing > Refunds", "Billing > Refunds > Annual plans"],
        )

    def test_heading_words_are_searchable(self):
        self.create_article(title="Billing", content=BODY)
        self.assertEqual(self.found("annual"), ["Billing > Refunds > Annual plans"])

    def test_edit_changes_what_is_searchable(self):
        data = self.create_article(title="Billing", content=BODY)
        self.owner_client.patch(
            self.kurl(f"articles/{data['id']}/"),
            {"content": "# Shipping\nParcels travel by air."},
            format="json",
        )
        self.assertEqual(self.found("refunds"), [])
        self.assertEqual(self.found("parcel"), ["Billing > Shipping"])

    def test_language_change_recomputes_vectors(self):
        self.create_article(title="Facturas", content="# Pagos\nLos reembolsos tardan.")
        self.assertEqual(self.found("reembolso", "spanish"), [])
        self.set_language("spanish")
        self.assertEqual(self.found("reembolso", "spanish"), ["Facturas > Pagos"])
