from knowledge.models import KnowledgeArticle, KnowledgeCategory
from knowledge.tests.base import KnowledgeTestCase


class CategoryTests(KnowledgeTestCase):
    def names(self, workspace_id=None, client=None):
        client = client or self.member_client
        response = client.get(self.kurl("categories/", workspace_id))
        return [i["name"] for i in response.data["data"]["items"]]

    def test_defaults_are_seeded_when_a_workspace_is_created(self):
        fresh = self.create_workspace(name="Fresh")["id"]
        self.assertEqual(
            self.names(fresh, self.owner_client),
            ["Billing", "FAQ", "General", "Getting started", "Troubleshooting"],
        )

    def test_seeding_is_idempotent(self):
        from knowledge.services import category_service

        category_service.seed_defaults(self.workspace_id)
        category_service.seed_defaults(self.workspace_id)
        self.assertEqual(
            KnowledgeCategory.objects.filter(workspace_id=self.workspace_id).count(), 5
        )

    def test_members_can_add_rename_delete(self):
        created = self.member_client.post(
            self.kurl("categories/"), {"name": " Shipping "}, format="json"
        )
        self.assertEqual(
            (
                created.status_code,
                created.data["data"]["name"],
                created.data["data"]["slug"],
            ),
            (201, "Shipping", "shipping"),
        )
        url = self.kurl(f"categories/{created.data['data']['id']}/")
        renamed = self.owner_client.patch(url, {"name": "Delivery"}, format="json")
        self.assertEqual(
            (renamed.status_code, renamed.data["data"]["slug"]), (200, "delivery")
        )
        self.assertEqual(self.member_client.delete(url).status_code, 200)
        self.assertNotIn("Delivery", self.names())

    def test_duplicate_name_conflicts_even_with_different_case(self):
        for name in ("faq", "FAQ", "F A Q".replace(" ", "")):
            response = self.owner_client.post(
                self.kurl("categories/"), {"name": name}, format="json"
            )
            self.assertEqual(
                (response.status_code, response.data["code"]),
                (409, "category_exists"),
                name,
            )
        faq = self.category_id("FAQ")
        general = self.category_id("General")
        clash = self.owner_client.patch(
            self.kurl(f"categories/{faq}/"), {"name": "general"}, format="json"
        )
        self.assertEqual(clash.status_code, 409)
        self.assertEqual(KnowledgeCategory.objects.get(pk=general).name, "General")

    def test_same_name_allowed_in_another_workspace(self):
        other = self.create_workspace(client=self.stranger_client, name="Theirs")["id"]
        self.assertEqual(
            self.stranger_client.post(
                self.kurl("categories/", other), {"name": "Shipping"}, format="json"
            ).status_code,
            201,
        )
        self.assertEqual(
            self.owner_client.post(
                self.kurl("categories/"), {"name": "Shipping"}, format="json"
            ).status_code,
            201,
        )

    def test_deleting_a_category_keeps_its_articles(self):
        faq = self.category_id("FAQ")
        data = self.create_article(category_ids=[faq])
        self.owner_client.delete(self.kurl(f"categories/{faq}/"))
        article = self.owner_client.get(self.kurl(f"articles/{data['id']}/")).data[
            "data"
        ]
        self.assertEqual(article["categories"], [])
        self.assertEqual(KnowledgeArticle.objects.count(), 1)

    def test_validation_and_isolation(self):
        for body in ({}, {"name": ""}, {"name": "x" * 61}, {"name": "ok", "extra": 1}):
            self.assertEqual(
                self.owner_client.post(
                    self.kurl("categories/"), body, format="json"
                ).status_code,
                400,
                body,
            )
        faq = self.category_id("FAQ")
        other = self.create_workspace(client=self.stranger_client, name="Theirs")["id"]
        url = self.kurl(f"categories/{faq}/", other)  # right id, wrong workspace
        self.assertEqual(
            self.stranger_client.patch(
                url, {"name": "Hijack"}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(self.stranger_client.delete(url).status_code, 404)
        self.assertEqual(
            self.stranger_client.get(self.kurl("categories/")).status_code, 404
        )
        self.assertEqual(KnowledgeCategory.objects.get(pk=faq).name, "FAQ")
