from django.db import models


class TicketStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In progress"
    PENDING = "pending", "Pending"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"


class TicketPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class TicketCategory(models.TextChoices):
    """Fixed list; not customisable per workspace."""

    BILLING = "billing", "Billing"
    TECHNICAL = "technical", "Technical"
    ACCOUNT = "account", "Account"
    FEATURE_REQUEST = "feature_request", "Feature request"
    GENERAL = "general", "General"
    OTHER = "other", "Other"


class TicketSource(models.TextChoices):
    PORTAL = "portal", "Portal"
    AGENT = "agent", "Agent"
    EMAIL = "email", "Email"


class AuthorType(models.TextChoices):
    AGENT = "agent", "Agent"
    CUSTOMER = "customer", "Customer"
    SYSTEM = "system", "System"


class MessageVisibility(models.TextChoices):
    PUBLIC = "public", "Customer-visible"
    INTERNAL = "internal", "Internal note"


class MessageDirection(models.TextChoices):
    INBOUND = "inbound", "Inbound"
    OUTBOUND = "outbound", "Outbound"
    INTERNAL = "internal", "Internal"


class DeliveryStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    RECEIVED = "received", "Received"


class EventType(models.TextChoices):
    CREATED = "created", "Created"
    STATUS_CHANGED = "status_changed", "Status changed"
    PRIORITY_CHANGED = "priority_changed", "Priority changed"
    CATEGORY_CHANGED = "category_changed", "Category changed"
    ASSIGNEE_CHANGED = "assignee_changed", "Assignee changed"
    DETAILS_CHANGED = "details_changed", "Details changed"
    PUBLIC_REPLY_ADDED = "public_reply_added", "Public reply added"
    INTERNAL_NOTE_ADDED = "internal_note_added", "Internal note added"
    CUSTOMER_REPLY_RECEIVED = "customer_reply_received", "Customer reply received"
    EMAIL_DELIVERY_FAILED = "email_delivery_failed", "Email delivery failed"
