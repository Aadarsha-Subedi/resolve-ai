from datetime import timedelta

from django.utils import timezone

from audit.models import AuditEvent
from email_integration.tests.base import EmailTestCase
from knowledge.tests.base import KnowledgeTestCase
from workspaces.models import WorkspaceMembership


class WorkspaceEventTests(EmailTestCase):
    def events(self, **filters):
        return AuditEvent.objects.filter(workspace_id=self.workspace_id, **filters)

    def test_workspace_creation_is_recorded_with_its_owner(self):
        event = self.events(action="workspace.created").get()
        self.assertEqual(
            (event.actor_user, event.actor_name, event.target_type, event.target_id),
            (self.owner, "owner", "workspace", self.workspace_id),
        )

    def test_update_records_which_fields_changed_not_their_values(self):
        self.owner_client.patch(
            f"/api/workspaces/{self.workspace_id}/",
            {"name": "Renamed", "portal_enabled": False},
            format="json",
        )
        event = self.events(action="workspace.updated").get()
        self.assertEqual(sorted(event.metadata["fields"]), ["name", "portal_enabled"])
        self.assertNotIn("Renamed", str(event.metadata))

    def test_join_link_and_joining_never_store_the_token(self):
        issued = self.owner_client.post(
            f"/api/workspaces/{self.workspace_id}/join-link/",
            {"expires_in": "1d"},
            format="json",
        )
        token = issued.data["data"]["token"]
        self.stranger_client.post(
            "/api/join-links/redeem/", {"token": token}, format="json"
        )
        created = self.events(action="join_link.created").get()
        self.assertEqual(
            (created.actor_user, created.metadata), (self.owner, {"expires_in": "1d"})
        )
        joined = self.events(action="member.joined").get()
        self.assertEqual(
            (joined.actor_user, joined.target_id),
            (self.stranger, str(self.stranger.pk)),
        )
        self.assertNotIn(token, str(list(AuditEvent.objects.values())))
        self.owner_client.delete(f"/api/workspaces/{self.workspace_id}/join-link/")
        self.assertEqual(self.events(action="join_link.revoked").count(), 1)

    def test_removal_leaving_and_ownership_transfer(self):
        self.owner_client.delete(
            f"/api/workspaces/{self.workspace_id}/members/{self.member.pk}/"
        )
        removed = self.events(action="member.removed").get()
        self.assertEqual(
            (removed.actor_user, removed.target_type, removed.target_id),
            (self.owner, "user", str(self.member.pk)),
        )
        WorkspaceMembership.objects.filter(user=self.member).update(status="active")
        self.owner_client.post(
            f"/api/workspaces/{self.workspace_id}/transfer-ownership/",
            {"user_id": str(self.member.pk)},
            format="json",
        )
        moved = self.events(action="ownership.transferred").get()
        self.assertEqual(
            (moved.actor_user, moved.target_id), (self.owner, str(self.member.pk))
        )
        self.member_client.post(
            f"/api/workspaces/{self.workspace_id}/leave/"
        )  # now owner: refused, nothing recorded
        self.owner_client.post(f"/api/workspaces/{self.workspace_id}/leave/")
        self.assertEqual(self.events(action="member.left").get().actor_user, self.owner)

    def test_invitations_store_a_count_not_addresses(self):
        self.owner_client.post(
            f"/api/workspaces/{self.workspace_id}/invitations/",
            {"emails": ["x@example.com", "y@example.com"]},
            format="json",
        )
        event = self.events(action="invitation.created").get()
        self.assertEqual(event.metadata, {"count": 2})
        self.assertNotIn("example.com", str(list(AuditEvent.objects.values())))

    def test_failed_actions_leave_no_trace(self):
        self.member_client.patch(
            f"/api/workspaces/{self.workspace_id}/", {"name": "x"}, format="json"
        )  # 403
        self.owner_client.post(
            f"/api/workspaces/{self.workspace_id}/transfer-ownership/",
            {"user_id": str(self.stranger.pk)},
            format="json",
        )  # 400
        self.assertEqual(
            self.events(
                action__in=["workspace.updated", "ownership.transferred"]
            ).count(),
            0,
        )

    def test_deleting_a_workspace_is_recorded_and_purging_removes_its_log(self):
        self.owner_client.delete(f"/api/workspaces/{self.workspace_id}/")
        self.assertEqual(self.events(action="workspace.deleted").count(), 1)
        from workspaces.models import Workspace
        from workspaces.services import workspace_service

        Workspace.all_objects.filter(pk=self.workspace_id).update(
            deleted_at=timezone.now() - timedelta(days=8)
        )
        workspace_service.purge_due_workspaces()
        self.assertEqual(self.events().count(), 0)  # rows are purged with the workspace
        self.assertFalse(AuditEvent.objects.filter(action="workspace.purged").exists())


class TicketEventTests(EmailTestCase):
    def events(self, **filters):
        return AuditEvent.objects.filter(workspace_id=self.workspace_id, **filters)

    def test_ticket_lifecycle(self):
        ticket = self.new_ticket()
        created = self.events(action="ticket.created").get()
        self.assertEqual(
            (created.actor_user, created.target_type, created.target_id),
            (self.member, "ticket", ticket["id"]),
        )
        self.set_status(ticket["id"], "closed")
        self.set_status(ticket["id"], "open", client=self.owner_client)
        changes = [
            (e.metadata["old"], e.metadata["new"], e.actor_user)
            for e in self.events(action="ticket.status_changed").order_by(
                "created_at", "id"
            )
        ]
        self.assertEqual(
            changes, [("open", "closed", self.member), ("closed", "open", self.owner)]
        )
        self.member_client.patch(
            f"/api/workspaces/{self.workspace_id}/tickets/{ticket['id']}/",
            {"priority": "high", "subject": "New"},
            format="json",
        )
        self.assertEqual(
            sorted(self.events(action="ticket.updated").get().metadata["fields"]),
            ["priority", "subject"],
        )

    def test_portal_tickets_have_no_actor(self):
        self.api(
            self.anon,
            "post",
            "/api/portal/acme/tickets/",
            {"subject": "s", "description": "d", "customer_email": "c@example.com"},
        )
        event = self.events(action="ticket.created").get()
        self.assertEqual(
            (event.actor_user, event.actor_name, event.metadata),
            (None, "", {"source": "portal"}),
        )
        self.assertNotIn("c@example.com", str(list(AuditEvent.objects.values())))

    def test_conversation_content_is_not_audited(self):
        ticket = self.new_ticket()
        self.reply(ticket["id"], "Top secret reply text")
        self.reply(ticket["id"], "Top secret note", visibility="internal")
        self.assertFalse(
            AuditEvent.objects.filter(
                action__in=["ticket.reply_added", "ticket.note_added"]
            ).exists()
        )
        self.assertNotIn("Top secret", str(list(AuditEvent.objects.values())))


class KnowledgeEventTests(KnowledgeTestCase):
    def test_article_category_and_upload_events_point_at_their_target(self):
        article = self.create_article(
            title="Reset password", content="secret body text"
        )
        self.owner_client.post(self.kurl(f"articles/{article['id']}/publish/"))
        self.owner_client.patch(
            self.kurl(f"articles/{article['id']}/"),
            {"title": "Reset it"},
            format="json",
        )
        with self.captureOnCommitCallbacks(execute=True):
            self.owner_client.delete(self.kurl(f"articles/{article['id']}/"))
        actions = list(
            AuditEvent.objects.filter(
                workspace_id=self.workspace_id, target_id=article["id"]
            )
            .order_by("created_at", "id")
            .values_list("action", flat=True)
        )
        self.assertEqual(
            actions,
            [
                "article.created",
                "article.published",
                "article.updated",
                "article.deleted",
            ],
        )
        category = self.owner_client.post(
            self.kurl("categories/"), {"name": "Shipping"}, format="json"
        ).data["data"]["id"]
        self.owner_client.delete(self.kurl(f"categories/{category}/"))
        self.assertEqual(
            AuditEvent.objects.filter(
                action="category.deleted", target_id=category
            ).count(),
            1,
        )
        self.assertNotIn("secret body text", str(list(AuditEvent.objects.values())))

    def test_upload_events(self):
        body = self.owner_client.post(
            self.kurl("uploads/upload-url/"),
            {"filename": "a.txt", "content_type": "text/plain", "size": 5},
            format="json",
        ).data["data"]
        from knowledge.models import KnowledgeUpload

        self.storage.simulate_browser_put(
            KnowledgeUpload.objects.get().storage_key, b"hello"
        )
        self.owner_client.post(self.kurl(f"uploads/{body['id']}/confirm/"))
        self.owner_client.delete(self.kurl(f"uploads/{body['id']}/"))
        actions = list(
            AuditEvent.objects.filter(target_id=body["id"])
            .order_by("created_at", "id")
            .values_list("action", flat=True)
        )
        self.assertEqual(actions, ["upload.confirmed", "upload.deleted"])


class AccountLevelEventTests(EmailTestCase):
    def test_account_events_have_no_workspace(self):
        self.owner_client.post("/api/auth/logout-all/")
        event = AuditEvent.objects.get(action="logout_all")
        self.assertEqual(
            (event.workspace, event.actor_user, event.target_id),
            (None, self.owner, str(self.owner.pk)),
        )

    def test_account_deletion_request(self):
        self.stranger_client.delete("/api/me/")
        self.assertEqual(
            AuditEvent.objects.filter(
                action="deletion_requested", actor_user=self.stranger
            ).count(),
            1,
        )

    def test_gmail_connection_changes_are_recorded_without_tokens(self):
        from email_integration.services import connection_service

        self.connect(self.member)
        connection = connection_service.get_connection(self.member)
        connection_service.mark_reauth_required(connection)
        connection.refresh_from_db()
        connection.status = "connected"
        connection.save()
        connection_service.disconnect(self.member)
        actions = list(
            AuditEvent.objects.filter(actor_user=self.member)
            .order_by("created_at", "id")
            .values_list("action", flat=True)
        )
        self.assertEqual(actions, ["gmail.reauth_required", "gmail.disconnected"])
        self.assertNotIn("refresh", str(list(AuditEvent.objects.values())))
