from django.test import override_settings

from knowledge.models import KnowledgeArticle
from knowledge.tests.base import KnowledgeTestCase


@override_settings(WORKSPACE_MAX_ARTICLES=3)
class ArticleLimitTests(KnowledgeTestCase):
    def post(self, title="t", client=None):
        return (client or self.owner_client).post(
            self.kurl("articles/"), {"title": title, "content": "x"}, format="json"
        )

    def test_the_article_past_the_limit_is_rejected(self):
        for i in range(3):
            self.assertEqual(self.post(f"a{i}").status_code, 201)
        response = self.post("one too many")
        self.assertEqual(
            (response.status_code, response.data["code"]),
            (409, "article_limit_reached"),
        )
        self.assertEqual(KnowledgeArticle.objects.count(), 3)
        self.assertEqual(self.used(), 3)  # nothing reserved for the rejected one

    def test_deleting_frees_a_slot(self):
        ids = [self.post(f"a{i}").data["data"]["id"] for i in range(3)]
        self.owner_client.delete(self.kurl(f"articles/{ids[0]}/"))
        self.assertEqual(self.post("again").status_code, 201)

    def test_archived_articles_still_count(self):
        ids = [self.post(f"a{i}").data["data"]["id"] for i in range(3)]
        self.owner_client.post(self.kurl(f"articles/{ids[0]}/archive/"))
        self.assertEqual(self.post("again").status_code, 409)

    def test_editing_is_not_blocked_at_the_limit(self):
        ids = [self.post(f"a{i}").data["data"]["id"] for i in range(3)]
        response = self.owner_client.patch(
            self.kurl(f"articles/{ids[0]}/"), {"title": "renamed"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_limit_is_per_workspace(self):
        for i in range(3):
            self.post(f"a{i}")
        other = self.create_workspace(name="Other")["id"]
        response = self.owner_client.post(
            self.kurl("articles/", workspace_id=other),
            {"title": "t", "content": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
