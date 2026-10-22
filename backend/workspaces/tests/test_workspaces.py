from datetime import timedelta
from unittest import mock, skipUnless

from django.db import connection
from django.test import override_settings
from django.utils import timezone

from accounts.services import deletion_service
from common.storage.memory import InMemoryStorage
from workspaces.constants.roles import MembershipStatus, Role
from workspaces.constants.settings import SEARCH_LANGUAGE_CHOICES
from workspaces.models import Workspace, WorkspaceMembership
from workspaces.services import workspace_service
from workspaces.tasks import purge_deleted_workspaces
from workspaces.tests.base import WorkspaceTestCase


class CreateWorkspaceTests(WorkspaceTestCase):
    def test_creator_becomes_the_single_owner(self):
        data = self.create_workspace(name="Acme Support")
        self.assertEqual(data["role"], "owner")
        self.assertTrue(data["slug"].startswith("acme-support-"))
        self.assertTrue(data["portal_enabled"])
        membership = WorkspaceMembership.objects.get(workspace_id=data["id"])
        self.assertEqual((membership.user, membership.role), (self.owner, Role.OWNER))

    def test_custom_slug(self):
        self.assertEqual(self.create_workspace(slug="Acme-Help")["slug"], "acme-help")

    def test_slug_taken_reserved_and_invalid(self):
        self.create_workspace(slug="acme")
        taken = self.owner_client.post(
            "/api/workspaces/", {"name": "B", "slug": "acme"}, format="json"
        )
        self.assertEqual((taken.status_code, taken.data["code"]), (409, "slug_taken"))
        reserved = self.owner_client.post(
            "/api/workspaces/", {"name": "B", "slug": "admin"}, format="json"
        )
        self.assertEqual(
            (reserved.status_code, reserved.data["code"]), (400, "slug_reserved")
        )
        for bad in ("a", "-ab", "ab-", "has space", "UPPER_case", "x" * 41):
            response = self.owner_client.post(
                "/api/workspaces/", {"name": "B", "slug": bad}, format="json"
            )
            self.assertEqual(response.status_code, 400, bad)

    def test_validation(self):
        for body in (
            {},
            {"name": ""},
            {"name": "x" * 81},
            {"name": "A", "owner": "me"},
        ):
            response = self.owner_client.post("/api/workspaces/", body, format="json")
            self.assertEqual(response.status_code, 400, body)

    def test_requires_authentication(self):
        from rest_framework.test import APIClient

        self.assertEqual(
            APIClient().post("/api/workspaces/", {"name": "A"}).status_code, 401
        )


class ReadAndIsolationTests(WorkspaceTestCase):
    def test_list_only_my_active_workspaces(self):
        mine = self.create_workspace(name="Mine")
        other = self.create_workspace(client=self.stranger_client, name="Theirs")
        response = self.owner_client.get("/api/workspaces/")
        ids = [i["id"] for i in response.data["data"]["items"]]
        self.assertEqual(ids, [mine["id"]])
        self.assertNotIn(other["id"], ids)
        self.assertEqual(response.data["meta"]["count"], 1)

    def test_non_member_gets_404_everywhere(self):
        workspace_id = self.workspace_with_member()
        uid = "0192e9e0-0000-7000-8000-000000000001"
        checks = [
            ("get", "", {}),
            ("patch", "", {"name": "X"}),
            ("delete", "", {}),
            ("get", "members/", {}),
            ("delete", f"members/{uid}/", {}),
            ("post", "leave/", {}),
            ("get", "join-link/", {}),
            ("post", "join-link/", {}),
            ("delete", "join-link/", {}),
            ("get", "invitations/", {}),
            ("post", "invitations/", {"emails": ["a@example.com"]}),
            ("delete", f"invitations/{uid}/", {}),
            ("post", "transfer-ownership/", {"user_id": uid}),
            ("post", "logo/upload-url/", {"content_type": "image/png", "size": 10}),
            ("put", "logo/", {"key": "k"}),
            ("delete", "logo/", {}),
        ]
        for method, suffix, body in checks:
            response = getattr(self.stranger_client, method)(
                self.url(workspace_id, suffix), body, format="json"
            )
            self.assertEqual(response.status_code, 404, (method, suffix))

    def test_removed_member_loses_access(self):
        workspace_id = self.workspace_with_member()
        WorkspaceMembership.objects.filter(user=self.member).update(
            status=MembershipStatus.REMOVED
        )
        self.assertEqual(
            self.member_client.get(self.url(workspace_id)).status_code, 404
        )
        self.assertEqual(
            self.member_client.get("/api/workspaces/").data["meta"]["count"], 0
        )

    def test_member_sees_workspace_with_role(self):
        workspace_id = self.workspace_with_member()
        response = self.member_client.get(self.url(workspace_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["role"], "member")

    def test_unknown_workspace_is_404(self):
        response = self.owner_client.get(
            self.url("0192e9e0-0000-7000-8000-000000000000")
        )
        self.assertEqual(response.status_code, 404)


class UpdateWorkspaceTests(WorkspaceTestCase):
    def test_owner_updates_name_and_portal(self):
        workspace_id = self.create_workspace()["id"]
        response = self.owner_client.patch(
            self.url(workspace_id),
            {"name": " Renamed ", "portal_enabled": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        workspace = Workspace.objects.get(pk=workspace_id)
        self.assertEqual((workspace.name, workspace.portal_enabled), ("Renamed", False))

    def test_member_cannot_update(self):
        workspace_id = self.workspace_with_member()
        response = self.member_client.patch(
            self.url(workspace_id), {"name": "X"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Workspace.objects.get(pk=workspace_id).name, "Acme Support")

    def test_slug_is_immutable_and_unknown_fields_rejected(self):
        data = self.create_workspace()
        for body in ({"slug": "new-slug"}, {"role": "owner"}, {}):
            response = self.owner_client.patch(
                self.url(data["id"]), body, format="json"
            )
            self.assertEqual(response.status_code, 400, body)
        self.assertEqual(Workspace.objects.get(pk=data["id"]).slug, data["slug"])


class SearchLanguageTests(WorkspaceTestCase):
    def test_defaults_to_english(self):
        data = self.create_workspace()
        self.assertEqual(data["search_language"], "english")

    def test_owner_changes_language(self):
        workspace_id = self.create_workspace()["id"]
        response = self.owner_client.patch(
            self.url(workspace_id), {"search_language": "spanish"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["search_language"], "spanish")
        self.assertEqual(
            Workspace.objects.get(pk=workspace_id).search_language, "spanish"
        )

    def test_unknown_language_rejected(self):
        workspace_id = self.create_workspace()["id"]
        for bad in ("klingon", "", "ENGLISH; DROP TABLE x"):
            response = self.owner_client.patch(
                self.url(workspace_id), {"search_language": bad}, format="json"
            )
            self.assertEqual(response.status_code, 400, bad)
        self.assertEqual(
            Workspace.objects.get(pk=workspace_id).search_language, "english"
        )

    def test_member_cannot_change_language(self):
        workspace_id = self.workspace_with_member()
        response = self.member_client.patch(
            self.url(workspace_id), {"search_language": "simple"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    @skipUnless(connection.vendor == "postgresql", "needs pg_ts_config")
    def test_every_choice_is_a_postgres_text_search_config(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT cfgname FROM pg_ts_config")
            available = {row[0] for row in cursor.fetchall()}
        offered = {value for value, _ in SEARCH_LANGUAGE_CHOICES}
        self.assertEqual(offered - available, set())


@override_settings(USER_MAX_OWNED_WORKSPACES=2)
class OwnedWorkspaceLimitTests(WorkspaceTestCase):
    def create(self, client=None, name="W"):
        return (client or self.owner_client).post(
            "/api/workspaces/", {"name": name}, format="json"
        )

    def test_creating_past_the_limit_is_rejected(self):
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(self.create().status_code, 201)
        response = self.create()
        self.assertEqual(
            (response.status_code, response.data["code"]),
            (409, "workspace_limit_reached"),
        )
        self.assertEqual(Workspace.objects.count(), 2)

    def test_joined_workspaces_do_not_count(self):
        for _ in range(2):
            self.workspace_with_member()  # member joins two workspaces owned by owner
        self.assertEqual(self.create(self.member_client).status_code, 201)
        self.assertEqual(self.create(self.member_client).status_code, 201)

    def test_deleted_workspaces_do_not_count(self):
        first = self.create().data["data"]["id"]
        self.create()
        self.owner_client.delete(self.url(first))
        self.assertEqual(self.create().status_code, 201)

    def test_transfer_to_a_user_at_the_limit_is_rejected(self):
        self.create(self.member_client)
        self.create(self.member_client)
        workspace_id = self.workspace_with_member()
        response = self.owner_client.post(
            self.url(workspace_id, "transfer-ownership/"),
            {"user_id": str(self.member.id)},
            format="json",
        )
        self.assertEqual(
            (response.status_code, response.data["code"]),
            (409, "transfer_target_at_limit"),
        )
        self.assertEqual(
            WorkspaceMembership.objects.get(
                workspace_id=workspace_id, user=self.owner
            ).role,
            Role.OWNER,
        )


class DeleteWorkspaceTests(WorkspaceTestCase):
    def test_owner_deletes_and_it_disappears(self):
        workspace_id = self.workspace_with_member()
        self.assertEqual(
            self.owner_client.delete(self.url(workspace_id)).status_code, 200
        )
        for client in (self.owner_client, self.member_client):
            self.assertEqual(client.get(self.url(workspace_id)).status_code, 404)
            self.assertEqual(client.get("/api/workspaces/").data["meta"]["count"], 0)
        self.assertTrue(Workspace.all_objects.get(pk=workspace_id).is_deleted)

    def test_member_cannot_delete(self):
        workspace_id = self.workspace_with_member()
        self.assertEqual(
            self.member_client.delete(self.url(workspace_id)).status_code, 403
        )
        self.assertFalse(Workspace.objects.get(pk=workspace_id).is_deleted)

    def test_purge_after_grace_period_only(self):
        keep = self.create_workspace(name="Keep")["id"]
        recent = self.create_workspace(name="Recent")["id"]
        old = self.create_workspace(name="Old")["id"]
        for workspace_id in (recent, old):
            self.owner_client.delete(self.url(workspace_id))
        now = timezone.now()
        Workspace.all_objects.filter(pk=recent).update(
            deleted_at=now - timedelta(days=6)
        )
        Workspace.all_objects.filter(pk=old).update(
            deleted_at=now - timedelta(days=7, minutes=1)
        )
        self.assertEqual(purge_deleted_workspaces(), 1)
        self.assertEqual(
            set(Workspace.all_objects.values_list("pk", flat=True)),
            {__import__("uuid").UUID(keep), __import__("uuid").UUID(recent)},
        )
        self.assertFalse(WorkspaceMembership.objects.filter(workspace_id=old).exists())

    def test_purge_removes_logo_object(self):
        storage = InMemoryStorage()
        storage.upload("workspaces/x/logo/a.png", b"x", "image/png")
        workspace_id = self.create_workspace()["id"]
        Workspace.objects.filter(pk=workspace_id).update(
            logo_key="workspaces/x/logo/a.png"
        )
        self.owner_client.delete(self.url(workspace_id))
        Workspace.all_objects.filter(pk=workspace_id).update(
            deleted_at=timezone.now() - timedelta(days=8)
        )
        with mock.patch("common.storage.get_storage", return_value=storage):
            workspace_service.purge_due_workspaces()
        self.assertEqual(storage.objects, {})


class AccountDeletionIntegrationTests(WorkspaceTestCase):
    def test_owner_cannot_delete_account_until_ownership_moves(self):
        workspace_id = self.workspace_with_member()
        response = self.owner_client.delete("/api/me/")
        self.assertEqual(
            (response.status_code, response.data["code"]),
            (409, "account_owns_workspace"),
        )
        self.assertIn("Acme Support", response.data["errors"][0]["message"])
        self.owner_client.post(
            self.url(workspace_id, "transfer-ownership/"),
            {"user_id": str(self.member.id)},
            format="json",
        )
        self.assertEqual(self.owner_client.delete("/api/me/").status_code, 200)

    def test_member_can_delete_account(self):
        self.workspace_with_member()
        self.assertEqual(self.member_client.delete("/api/me/").status_code, 200)

    def test_owner_of_only_a_deleted_workspace_can_delete_account(self):
        workspace_id = self.create_workspace()["id"]
        self.owner_client.delete(self.url(workspace_id))
        self.assertEqual(deletion_service.ownership_blockers(self.owner), [])
