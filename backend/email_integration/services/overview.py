from accounts.models import User
from email_integration.serializers.responses import ConnectionData
from email_integration.services import connection_service
from tickets.models import Ticket


def gmail_status_block(user: User, ticket: Ticket) -> dict:
    """Part of the ticket overview: can the viewer email the customer from their Gmail?"""
    return ConnectionData(connection_service.get_connection(user)).to_dict()
