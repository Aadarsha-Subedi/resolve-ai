from django.test import override_settings

from email_integration.clients.base import GmailAuthError, GmailTransientError
from email_integration.constants.enums import ConnectionStatus
from email_integration.models import GmailConnection
from email_integration.services import send_service
from email_integration.tests.base import EmailTestCase
from workspaces.models import WorkspaceInvitation


@override_settings(FRONTEND_URL="https://app.example.com/")
class InvitationEmailTests(EmailTestCase):
    def invite(self, emails, client=None):
        return self.api(
            client or self.owner_client,
            "post",
            self.url(self.workspace_id, "invitations/"),
            {"emails": emails},
        )

    def url(self, workspace_id, suffix=""):
        return f"/api/workspaces/{workspace_id}/{suffix}"

    def test_invitee_gets_an_email_from_the_owners_gmail(self):
        self.connect(self.owner)
        response = self.invite(["guest@example.com"])
        self.assertEqual(response.status_code, 201)
        sent = self.gmail(self.owner).sent
        self.assertEqual(len(sent), 1)
        mail = sent[0]["message"]
        self.assertEqual(mail["To"], "guest@example.com")
        self.assertIn("owner@example.com", mail["From"])
        self.assertIn("Acme Support", mail["Subject"])
        body = mail.get_payload()
        self.assertIn("owner invited you", body)
        self.assertIn("https://app.example.com/app/invitations", body)
        self.assertIsNotNone(WorkspaceInvitation.objects.get().notified_at)

    def test_one_email_per_new_invitation_and_none_for_duplicates(self):
        self.connect(self.owner)
        self.invite(["a@example.com", "b@example.com"])
        self.invite(["a@example.com"])  # already invited: no second email
        self.assertEqual(len(self.gmail(self.owner).sent), 2)

    def test_no_connected_gmail_skips_sending_but_invitation_is_created(self):
        response = self.invite(["guest@example.com"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.gmail(self.owner).sent, [])
        self.assertIsNone(WorkspaceInvitation.objects.get().notified_at)

    def test_reauth_required_connection_is_skipped(self):
        self.connect(self.owner, status=ConnectionStatus.REAUTH_REQUIRED)
        response = self.invite(["guest@example.com"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.gmail(self.owner).sent, [])

    def test_gmail_failure_never_breaks_invitation_creation(self):
        self.connect(self.owner)
        self.gmail(self.owner).fail_with = GmailTransientError("boom")
        response = self.invite(["guest@example.com"])
        self.assertEqual(response.status_code, 201)
        invitation = WorkspaceInvitation.objects.get()
        self.assertIsNone(invitation.notified_at)
        self.assertTrue(invitation.is_usable())

    def test_gmail_auth_error_marks_reauth_and_keeps_invitation(self):
        self.connect(self.owner)
        self.gmail(self.owner).fail_with = GmailAuthError("revoked")
        response = self.invite(["guest@example.com"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            GmailConnection.objects.get(user=self.owner).status,
            ConnectionStatus.REAUTH_REQUIRED,
        )

    def test_task_is_idempotent_and_skips_closed_invitations(self):
        self.connect(self.owner)
        self.invite(["guest@example.com"])
        invitation = WorkspaceInvitation.objects.get()
        send_service.send_invitation_email(invitation.id)  # already notified
        self.assertEqual(len(self.gmail(self.owner).sent), 1)
        other = WorkspaceInvitation.objects.create(
            workspace_id=self.workspace_id,
            email="x@example.com",
            email_key="x@example.com",
            invited_by=self.owner,
            expires_at=invitation.expires_at,
            closed_at=invitation.created_at,
        )
        send_service.send_invitation_email(other.id)
        self.assertEqual(len(self.gmail(self.owner).sent), 1)

    def test_logs_never_contain_the_invitee_address(self):
        self.connect(self.owner)
        with self.assertLogs("email_integration", level="INFO") as logs:
            self.gmail(self.owner).fail_with = GmailTransientError("boom")
            self.invite(["secret.guest@example.com"])
        self.assertNotIn("secret.guest", "\n".join(logs.output))

    def test_member_cannot_invite(self):
        self.connect(self.member)
        response = self.invite(["guest@example.com"], client=self.member_client)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.gmail(self.member).sent, [])
