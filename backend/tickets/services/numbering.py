from django.db.models import F

from workspaces.models import Workspace


def next_ticket_number(workspace_id) -> int:
    """Hand out the next per-workspace number: no gaps, no duplicates.

    The UPDATE takes the workspace row lock, so concurrent creators queue up and the
    read that follows (same transaction) sees exactly this caller's value. Call it inside
    the transaction that creates the ticket: a rollback gives the number back.
    """
    Workspace.all_objects.filter(pk=workspace_id).update(
        last_ticket_number=F("last_ticket_number") + 1
    )
    return Workspace.all_objects.values_list("last_ticket_number", flat=True).get(
        pk=workspace_id
    )
