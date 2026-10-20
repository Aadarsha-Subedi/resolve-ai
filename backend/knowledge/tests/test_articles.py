from knowledge.models import KnowledgeArticle
from knowledge.tests.base import KnowledgeTestCase


class ArticleCrudTests(KnowledgeTestCase):
    def test_create_stores_body_in_storage_and_counts_quota(self):
        data = self.create_article(
            content="héllo", category_ids=[self.category_id("FAQ")]
        )
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["size_bytes"], 6)  # UTF-8 bytes, not characters
        self.assertEqual(data["categories"][0]["name"], "FAQ")
        article = KnowledgeArticle.objects.get()
        self.assertTrue(
            article.storage_key.startswith(
                f"workspaces/{self.workspace_id}/knowledge/articles/"
            )
        )
        self.assertEqual(self.storage.objects[article.storage_key][0], "héllo".encode())
        self.assertEqual(self.used(), 6)

    def test_detail_returns_content_list_does_not(self):
        data = self.create_article(content="Body text")
        detail = self.member_client.get(self.kurl(f"articles/{data['id']}/"))
        self.assertEqual(detail.data["data"]["content"], "Body text")
        listed = self.member_client.get(self.kurl("articles/")).data["data"]["items"]
        self.assertNotIn("content", listed[0])

    def test_update_changes_quota_by_the_difference(self):
        data = self.create_article(content="x" * 100)
        url = self.kurl(f"articles/{data['id']}/")
        self.assertEqual(
            self.owner_client.patch(
                url, {"content": "y" * 300}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(self.used(), 300)
        response = self.member_client.patch(
            url, {"content": "z" * 40, "title": "New"}, format="json"
        )
        self.assertEqual(response.data["data"]["content"], "z" * 40)
        self.assertEqual((response.data["data"]["title"], self.used()), ("New", 40))
        self.assertEqual(
            self.storage.objects[KnowledgeArticle.objects.get().storage_key][0],
            b"z" * 40,
        )

    def test_delete_frees_quota_and_object(self):
        data = self.create_article(content="x" * 100)
        key = KnowledgeArticle.objects.get().storage_key
        with self.captureOnCommitCallbacks(
            execute=True
        ):  # the object is deleted after commit
            response = self.member_client.delete(self.kurl(f"articles/{data['id']}/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual((self.used(), key in self.storage.objects), (0, False))
        self.assertEqual(
            self.owner_client.get(self.kurl(f"articles/{data['id']}/")).status_code, 404
        )

    def test_validation(self):
        bad = [
            {},
            {"title": "", "content": "x"},
            {"title": "t"},
            {"title": "t", "content": "x", "extra": 1},
            {"title": "x" * 201, "content": "x"},
            {"title": "t", "content": "x", "category_ids": ["nope"]},
        ]
        for body in bad:
            self.assertEqual(
                self.owner_client.post(
                    self.kurl("articles/"), body, format="json"
                ).status_code,
                400,
                body,
            )
        self.assertEqual(KnowledgeArticle.objects.count(), 0)
        self.assertEqual(self.used(), 0)

    def test_article_size_limit(self):
        response = self.owner_client.post(
            self.kurl("articles/"),
            {"title": "t", "content": "x" * (200 * 1024 + 1)},
            format="json",
        )
        self.assertEqual(
            (response.status_code, response.data["code"]), (400, "article_too_large")
        )
        self.create_article(content="x" * (200 * 1024))  # exactly at the limit is fine

    def test_unknown_or_foreign_category_rejected(self):
        other = self.create_workspace(client=self.stranger_client, name="Theirs")["id"]
        from knowledge.services import category_service

        category_service.seed_defaults(other)
        foreign = self.category_id("FAQ", workspace_id=other)
        response = self.owner_client.post(
            self.kurl("articles/"),
            {"title": "t", "content": "x", "category_ids": [foreign]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_patch_rejected(self):
        data = self.create_article()
        self.assertEqual(
            self.owner_client.patch(
                self.kurl(f"articles/{data['id']}/"), {}, format="json"
            ).status_code,
            400,
        )

    def test_storage_failure_rolls_everything_back(self):
        self.storage.upload = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("down")
        )
        response = self.owner_client.post(
            self.kurl("articles/"), {"title": "t", "content": "abc"}, format="json"
        )
        self.assertEqual(
            (response.status_code, response.data["code"]), (503, "storage_unavailable")
        )
        self.assertEqual(KnowledgeArticle.objects.count(), 0)
        self.assertEqual(self.used(), 0)


class LifecycleTests(KnowledgeTestCase):
    def transition(self, article_id, action, client=None):
        return (client or self.owner_client).post(
            self.kurl(f"articles/{article_id}/{action}/")
        )

    def test_publish_unpublish_archive(self):
        data = self.create_article()
        published = self.transition(data["id"], "publish")
        self.assertEqual(
            (published.status_code, published.data["data"]["status"]),
            (200, "published"),
        )
        self.assertIsNotNone(published.data["data"]["published_at"])
        self.assertEqual(
            self.transition(data["id"], "unpublish", self.member_client).data["data"][
                "status"
            ],
            "draft",
        )
        self.transition(data["id"], "publish")
        self.assertEqual(
            self.transition(data["id"], "archive").data["data"]["status"], "archived"
        )
        self.assertEqual(
            self.transition(data["id"], "publish").data["data"]["status"], "published"
        )

    def test_invalid_transitions(self):
        data = self.create_article()
        again = self.transition(data["id"], "unpublish")  # draft -> draft
        self.assertEqual(
            (again.status_code, again.data["code"]), (409, "invalid_status_transition")
        )
        self.transition(data["id"], "publish")
        self.assertEqual(self.transition(data["id"], "publish").status_code, 409)

    def test_archived_article_is_read_only(self):
        data = self.create_article()
        self.transition(data["id"], "archive")
        response = self.owner_client.patch(
            self.kurl(f"articles/{data['id']}/"), {"title": "x"}, format="json"
        )
        self.assertEqual(
            (response.status_code, response.data["code"]), (409, "article_archived")
        )
        self.assertEqual(
            self.owner_client.get(self.kurl(f"articles/{data['id']}/")).status_code, 200
        )
        self.transition(data["id"], "unpublish")
        self.assertEqual(
            self.owner_client.patch(
                self.kurl(f"articles/{data['id']}/"), {"title": "x"}, format="json"
            ).status_code,
            200,
        )

    def test_status_cannot_be_set_through_patch(self):
        data = self.create_article()
        response = self.owner_client.patch(
            self.kurl(f"articles/{data['id']}/"), {"status": "published"}, format="json"
        )
        self.assertEqual(response.status_code, 400)


class FilterTests(KnowledgeTestCase):
    def setUp(self):
        super().setUp()
        self.billing = self.category_id("Billing")
        self.faq = self.category_id("FAQ")
        self.a = self.create_article(title="Refund policy", category_ids=[self.billing])
        self.b = self.create_article(title="Reset password", category_ids=[self.faq])
        self.c = self.create_article(
            title="Invoice FAQ", category_ids=[self.billing, self.faq]
        )
        self.owner_client.post(self.kurl(f"articles/{self.b['id']}/publish/"))

    def ids(self, query):
        response = self.member_client.get(self.kurl("articles/") + query)
        self.assertEqual(response.status_code, 200, response.content)
        return {i["id"] for i in response.data["data"]["items"]}

    def test_filters(self):
        self.assertEqual(self.ids(""), {self.a["id"], self.b["id"], self.c["id"]})
        self.assertEqual(self.ids("?title=reset"), {self.b["id"]})
        self.assertEqual(self.ids("?status=published"), {self.b["id"]})
        self.assertEqual(self.ids("?status=draft"), {self.a["id"], self.c["id"]})
        self.assertEqual(
            self.ids(f"?category={self.billing}"), {self.a["id"], self.c["id"]}
        )
        self.assertEqual(
            self.ids(f"?category={self.billing}&status=draft&title=invoice"),
            {self.c["id"]},
        )

    def test_category_filter_does_not_duplicate_rows(self):
        response = self.member_client.get(
            self.kurl("articles/") + f"?category={self.faq}"
        )
        self.assertEqual(response.data["meta"]["count"], 2)

    def test_ordering_and_pagination(self):
        titles = [
            i["title"]
            for i in self.member_client.get(self.kurl("articles/?ordering=title")).data[
                "data"
            ]["items"]
        ]
        self.assertEqual(titles, ["Invoice FAQ", "Refund policy", "Reset password"])
        page = self.member_client.get(
            self.kurl("articles/?ordering=title&limit=2&offset=2")
        )
        self.assertEqual(
            [i["title"] for i in page.data["data"]["items"]], ["Reset password"]
        )
        self.assertEqual(page.data["meta"]["count"], 3)

    def test_bad_filters(self):
        for query in (
            "?status=bogus",
            "?category=nope",
            "?ordering=content",
            "?ordering=-nonsense",
        ):
            self.assertEqual(
                self.member_client.get(self.kurl("articles/") + query).status_code,
                400,
                query,
            )


class IsolationTests(KnowledgeTestCase):
    def test_other_workspace_cannot_see_or_touch_articles(self):
        data = self.create_article()
        other = self.create_workspace(client=self.stranger_client, name="Theirs")["id"]
        self.assertEqual(
            self.stranger_client.get(self.kurl("articles/")).status_code, 404
        )
        # Same article id addressed through the stranger's own workspace.
        url = self.kurl(f"articles/{data['id']}/", workspace_id=other)
        for method in ("get", "delete"):
            self.assertEqual(
                getattr(self.stranger_client, method)(url).status_code, 404, method
            )
        self.assertEqual(
            self.stranger_client.patch(url, {"title": "x"}, format="json").status_code,
            404,
        )
        self.assertEqual(self.stranger_client.post(url + "publish/").status_code, 404)
        self.assertEqual(KnowledgeArticle.objects.get().title, "Reset password")
        self.assertEqual(
            self.stranger_client.get(self.kurl("articles/", workspace_id=other)).data[
                "meta"
            ]["count"],
            0,
        )

    def test_removed_member_loses_access(self):
        from workspaces.constants.roles import MembershipStatus
        from workspaces.models import WorkspaceMembership

        WorkspaceMembership.objects.filter(user=self.member).update(
            status=MembershipStatus.REMOVED
        )
        self.assertEqual(
            self.member_client.get(self.kurl("articles/")).status_code, 404
        )

    def test_requires_authentication(self):
        from rest_framework.test import APIClient

        self.assertEqual(APIClient().get(self.kurl("articles/")).status_code, 401)
