from django.urls import path

from tickets.views import context, portal, ticket

_W = "workspaces/<uuid:workspace_id>/tickets/"

urlpatterns = [
    path(_W, ticket.TicketListView.as_view(), name="ticket_list"),
    path(
        _W + "<uuid:ticket_id>/",
        ticket.TicketDetailView.as_view(),
        name="ticket_detail",
    ),
    path(
        _W + "<uuid:ticket_id>/overview/",
        ticket.TicketOverviewView.as_view(),
        name="ticket_overview",
    ),
    path(
        _W + "<uuid:ticket_id>/status/",
        ticket.TicketStatusView.as_view(),
        name="ticket_status",
    ),
    path(
        _W + "<uuid:ticket_id>/assignee/",
        ticket.TicketAssigneeView.as_view(),
        name="ticket_assignee",
    ),
    path(
        _W + "<uuid:ticket_id>/messages/",
        ticket.TicketMessageListView.as_view(),
        name="ticket_messages",
    ),
    path(
        _W + "<uuid:ticket_id>/context/",
        context.TicketContextView.as_view(),
        name="ticket_context",
    ),
    path(
        _W + "<uuid:ticket_id>/events/",
        ticket.TicketEventListView.as_view(),
        name="ticket_events",
    ),
    path("portal/<slug:slug>/", portal.PortalInfoView.as_view(), name="portal_info"),
    path(
        "portal/<slug:slug>/tickets/",
        portal.PortalTicketView.as_view(),
        name="portal_ticket",
    ),
]
