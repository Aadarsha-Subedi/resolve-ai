"""Which actions the audit log records, and what each one points at.

An action is recorded only if it is listed here: a new feature registers its sensitive
actions in this file (and emits them through its own hooks module). Conversation content
(`ticket.reply_added`, `ticket.note_added`) is deliberately not listed: that is the ticket's
own history, and message bodies never go into the audit log.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionSpec:
    target_type: str
    # metadata key that holds the target id (None: the target is the workspace or the actor)
    target_key: str | None = None
    # "workspace" = the workspace itself, "actor" = whoever did it
    default_target: str = ""
    # account-level actions have no workspace and are not shown in workspace logs
    account_level: bool = False


WORKSPACE = ActionSpec("workspace", default_target="workspace")
ACTOR = ActionSpec("user", default_target="actor")

ACTIONS: dict[str, ActionSpec] = {
    # workspaces
    "workspace.created": WORKSPACE,
    "workspace.updated": WORKSPACE,
    "workspace.deleted": WORKSPACE,
    "workspace.logo_changed": WORKSPACE,
    "member.joined": ACTOR,
    "member.left": ACTOR,
    "member.removed": ActionSpec("user", target_key="user_id"),
    "ownership.transferred": ActionSpec("user", target_key="new_owner_id"),
    "join_link.created": ActionSpec("join_link", default_target="workspace"),
    "join_link.revoked": ActionSpec("join_link", default_target="workspace"),
    "invitation.created": ActionSpec("invitation", default_target="workspace"),
    "invitation.revoked": ActionSpec("invitation", default_target="workspace"),
    "invitation.accepted": ActionSpec("invitation", default_target="workspace"),
    "invitation.declined": ActionSpec("invitation", default_target="workspace"),
    # knowledge base
    "article.created": ActionSpec("article", target_key="target_id"),
    "article.updated": ActionSpec("article", target_key="target_id"),
    "article.published": ActionSpec("article", target_key="target_id"),
    "article.unpublished": ActionSpec("article", target_key="target_id"),
    "article.archived": ActionSpec("article", target_key="target_id"),
    "article.deleted": ActionSpec("article", target_key="target_id"),
    "category.created": ActionSpec("category", target_key="target_id"),
    "category.updated": ActionSpec("category", target_key="target_id"),
    "category.deleted": ActionSpec("category", target_key="target_id"),
    "upload.confirmed": ActionSpec("upload", target_key="target_id"),
    "upload.deleted": ActionSpec("upload", target_key="target_id"),
    # tickets (status changes carry old and new, so closing and reopening are visible)
    "ticket.created": ActionSpec("ticket"),
    "ticket.updated": ActionSpec("ticket"),
    "ticket.status_changed": ActionSpec("ticket"),
    "ticket.assignee_changed": ActionSpec("ticket"),
    # account level (no workspace; stored for security investigations)
    "deletion_requested": ActionSpec(
        "user", default_target="actor", account_level=True
    ),
    "deletion_cancelled": ActionSpec(
        "user", default_target="actor", account_level=True
    ),
    "deleted": ActionSpec("user", default_target="actor", account_level=True),
    "logout_all": ActionSpec("user", default_target="actor", account_level=True),
    "session_revoked": ActionSpec("user", default_target="actor", account_level=True),
    "gmail.connected": ActionSpec(
        "gmail_connection", default_target="actor", account_level=True
    ),
    "gmail.reauth_required": ActionSpec(
        "gmail_connection", default_target="actor", account_level=True
    ),
    "gmail.disconnected": ActionSpec(
        "gmail_connection", default_target="actor", account_level=True
    ),
}
