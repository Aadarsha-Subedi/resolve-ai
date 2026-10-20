"""TicketPolicy: state-based (ABAC) rules that narrow the RBAC grants. Fixed in code."""

from common.exception.domain import PermissionDeniedException
from tickets.constants import errors, messages
from tickets.constants.enums import TicketStatus
from tickets.models import Ticket
from workspaces.models import WorkspaceMembership


class TicketPolicy:
    @staticmethod
    def can_edit_protected_fields(
        membership: WorkspaceMembership, ticket: Ticket
    ) -> bool:
        """Closed tickets lock subject, description, customer, category and priority for members."""
        return ticket.status != TicketStatus.CLOSED or membership.is_owner

    @staticmethod
    def can_change_status(
        membership: WorkspaceMembership, ticket: Ticket, new_status: str
    ) -> bool:
        """Only the owner moves a ticket out of CLOSED (reopening)."""
        if ticket.status == TicketStatus.CLOSED and new_status != TicketStatus.CLOSED:
            return membership.is_owner
        return True

    @staticmethod
    def can_send_public_reply(ticket: Ticket) -> bool:
        return ticket.status != TicketStatus.CLOSED

    @staticmethod
    def can_add_internal_note(ticket: Ticket) -> bool:
        return True

    @classmethod
    def ensure_can_edit(cls, membership: WorkspaceMembership, ticket: Ticket) -> None:
        if not cls.can_edit_protected_fields(membership, ticket):
            raise PermissionDeniedException(
                messages.MESSAGE_TICKET_CLOSED, error_code=errors.ERROR_TICKET_CLOSED
            )

    @classmethod
    def ensure_can_change_status(
        cls, membership: WorkspaceMembership, ticket: Ticket, new_status: str
    ) -> None:
        if not cls.can_change_status(membership, ticket, new_status):
            raise PermissionDeniedException(
                messages.MESSAGE_OWNER_ONLY_REOPEN,
                error_code=errors.ERROR_OWNER_ONLY_REOPEN,
            )

    @classmethod
    def ensure_can_reply(cls, ticket: Ticket) -> None:
        if not cls.can_send_public_reply(ticket):
            raise PermissionDeniedException(
                messages.MESSAGE_REPLY_ON_CLOSED, error_code=errors.ERROR_TICKET_CLOSED
            )
