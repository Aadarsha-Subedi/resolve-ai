# ResolveAI --- Low-Level Design (LLD)

## Class and Service Design for v1

**Status:** Draft, owner decisions of 2026-10-16 applied (section 14)\
**Backend:** Django + Django REST Framework\
**Database:** PostgreSQL\
**Frontend:** React + TypeScript\
**Authentication:** Google OAuth + server-side Django sessions\
**Email:** Gmail API with OAuth\
**AI:** Gemini API\
**Search:** PostgreSQL full-text search for published knowledge-base
content

------------------------------------------------------------------------

## 1. Design goals

1.  Keep persistent data models separate from business logic and
    external integrations.
2.  Enforce workspace isolation on the backend for every private
    workspace resource.
3.  Keep the ticket conversation as the canonical record; email is a
    delivery and synchronization channel.
4.  Require human review before AI-generated replies are sent.
5.  Apply authorization in backend services and API permissions, never
    only in the frontend.
6.  Keep Gmail OAuth tokens and the Gemini API key on the server.
7.  Avoid sending the entire knowledge base to Gemini; retrieve relevant
    published content first.
8.  Keep the design implementable as a Django modular monolith for v1.

## 2. Architecture and module boundaries

``` text
React / TypeScript
        |
        | HTTPS + session cookie + CSRF token
        v
Django REST Framework API
        |
        +-- accounts/       Google identity, sessions, user profile
        +-- workspaces/     workspace, membership, join links, policies
        +-- tickets/        tickets, messages, status, public portal
        +-- knowledge/      articles, categories, feedback, FTS search
        +-- ai/             Gemini adapter, retrieval, citations, usage logs
        +-- email_integration/
        |                   Gmail OAuth, send, inbound sync, deduplication
        +-- dashboard/      workspace metrics and activity
        +-- audit/           audit events
        |
        v
PostgreSQL
        |
        +-- Django ORM records
        +-- PostgreSQL full-text search
        +-- transactional outbox / sync checkpoints as needed
```

**Recommended structure:** start with a modular monolith, not
microservices. Keep modules separated by responsibility, but deploy the
Django API and background worker as separate processes if asynchronous
email synchronization is implemented.

------------------------------------------------------------------------

## 3. Core domain model

### 3.1 Entity relationship overview

``` mermaid
erDiagram
    USER ||--o{ WORKSPACE_MEMBERSHIP : has
    WORKSPACE ||--o{ WORKSPACE_MEMBERSHIP : includes
    WORKSPACE ||--o{ JOIN_LINK : issues
    USER ||--o| GMAIL_CONNECTION : connects
    WORKSPACE ||--o{ TICKET : owns
    USER o|--o{ TICKET : creates_as_agent
    TICKET ||--o{ TICKET_MESSAGE : contains
    TICKET ||--o{ TICKET_EVENT : records
    WORKSPACE ||--o{ KNOWLEDGE_ARTICLE : owns
    KNOWLEDGE_ARTICLE }o--o{ KNOWLEDGE_CATEGORY : categorized_as
    AI_MESSAGE ||--o{ AI_FEEDBACK : receives
    WORKSPACE ||--o{ KNOWLEDGE_UPLOAD : stores
    WORKSPACE ||--o{ AI_CONVERSATION : owns
    AI_CONVERSATION ||--o{ AI_MESSAGE : contains
    AI_MESSAGE ||--o{ AI_SOURCE : cites
    WORKSPACE ||--o{ AI_USAGE_LOG : records
    USER ||--o{ AI_USAGE_LOG : initiates
    WORKSPACE ||--o{ AUDIT_EVENT : records
```

The diagram is conceptual. The actual schema should use explicit
through-models where relationship metadata or uniqueness constraints are
needed.

### 3.2 `User`

**Purpose:** ResolveAI account and stable Google identity.

Suggested fields: - `id`: UUID primary key - `google_subject`: unique,
non-null Google OIDC `sub` - `email`: normalized email address -
`email_verified`: boolean from verified Google identity claims -
`display_name` - `avatar_url`: optional - `is_active` - `created_at`,
`updated_at`, `last_login_at`

Important rules: - Use Google's stable `sub` claim as the identity key,
not email alone. - Do not provide password signup or password-reset
flows in this design. - Use Django server-side sessions after Google
OAuth completes. - Treat email changes as profile/identity updates that
require a deliberate policy; never silently merge two accounts solely
because their email strings match. - A user may belong to multiple
workspaces.

Methods: - `update_profile(...)` - `can_delete_account()` --- false
while the user owns a workspace without a transferred owner.

### 3.3 `Workspace`

**Purpose:** Tenant boundary for shared team data.

Suggested fields: - `id`: UUID - `name` - `slug`: unique public
identifier, **immutable after creation** - `logo`:
optional file/object reference - `created_by`: FK to `User` -
`is_active` - `created_at`, `updated_at`

Rules: - Every workspace-owned record must be associated with
`workspace_id`, directly or through a parent whose workspace
relationship is verified. - Resolve the active workspace from an
authorized membership, not from an untrusted client-supplied ID alone. -
Public portal endpoints may resolve a workspace from its public slug,
but must not expose private workspace data. - Slug is a locator, not an
authorization secret.

### 3.4 `WorkspaceMembership`

**Purpose:** Connect users to workspaces and store their workspace role.

Fields: - `id`: UUID - `workspace_id` - `user_id` - `role`: `OWNER` or
`MEMBER` - `status`: `ACTIVE` or `REMOVED` - `joined_at`, `updated_at`

Constraints: - Unique `(workspace_id, user_id)`. - Each active workspace
has exactly one owner at the application-policy level. - Ownership
transfer must be transactional: promote the new owner, demote the old
owner, and record an audit event. - Removing a member revokes future
workspace access but does not delete historical ticket messages or audit
records.

### 3.5 `WorkspaceJoinLink`

**Purpose:** Shareable link that grants membership to a workspace.

Fields: - `id`: UUID - `workspace_id` - `token_hash`: unique hash of a
high-entropy random token - `created_by` - `created_at` - `expires_at`:
optional, if expiration is supported - `revoked_at`: nullable

Methods: - `rotate(actor)` - `revoke(actor)` - `redeem(raw_token, user)`

Rules: - Only the owner (or a separately authorized role, if introduced
later) can rotate or revoke the link. - Rotating a link invalidates the
previous link. - The raw token is shown only when generated; store a
hash rather than the raw token. - Redemption creates an active
membership directly; there is no approval-request workflow in v1. -
Rate-limit token redemption and avoid logging raw tokens.

### 3.6 `GmailConnection`

**Purpose:** Store a user's authorized Gmail connection.

Fields: - `id`: UUID - `user_id`: one-to-one relationship -
`google_subject`: Google account `sub` verified during Gmail OAuth -
`mailbox_email` - `encrypted_refresh_token` - `granted_scopes` -
`status`: `CONNECTED`, `REAUTH_REQUIRED`, `DISCONNECTED` -
`connected_at`, `last_sync_at`, `updated_at` - `history_id` or
equivalent sync checkpoint, if using Gmail history synchronization

Rules: - Enforce one connection per user. - `google_subject` must match
the user's authenticated Google identity `sub`; reject a connection for
a different Google account. - Google sign-in and Gmail authorization are
separate consent steps. - Encrypt refresh tokens at rest; never return
tokens from API serializers or expose them to the browser. - Request
only the Gmail scopes required for the agreed send/read/sync features. -
Disconnecting should revoke the connection where supported and remove or
invalidate stored credentials. - Never store a Google account password
or ask users to provide one.

------------------------------------------------------------------------

## 4. Ticketing module

### 4.1 Enums

Proposed enums (confirm final status lifecycle before implementation):

``` python
class TicketStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In Progress"
    PENDING = "pending", "Pending"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"

class TicketPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"

class MessageVisibility(models.TextChoices):
    PUBLIC = "public", "Customer-visible"
    INTERNAL = "internal", "Internal note"

class MessageDirection(models.TextChoices):
    INBOUND = "inbound", "Inbound"
    OUTBOUND = "outbound", "Outbound"
    INTERNAL = "internal", "Internal"
```

**Decision (confirmed):** `RESOLVED` and `CLOSED` are separate states,
with owner-only reopening after closure.

### 4.2 `Ticket`

**Purpose:** Canonical support case.

Fields: - `id`: UUID - `workspace_id` - `ticket_number`: human-readable
number unique within a workspace - `subject` - `description` or initial
request content - `customer_name`: optional - `customer_email` -
`status` - `priority` - `category`: fixed enum value (see 4.6) -
`created_by_user_id`: nullable; set for an authenticated agent-created
ticket, not for anonymous customers - `created_via`: `PORTAL`, `AGENT`,
or `EMAIL` - `created_at`, `updated_at`, `resolved_at`, `closed_at` -
`last_customer_message_at`, `last_agent_reply_at` - `last_activity_at`

Methods should delegate policy-sensitive changes to a service rather
than directly mutating state: - `change_status(...)` ---
service-controlled - `change_priority(...)` - `change_category(...)`

Constraints/indexes: - Unique `(workspace_id, ticket_number)`. - Index
`(workspace_id, status, updated_at)`. - Index
`(workspace_id, priority, created_at)`. - Index
`(workspace_id, customer_email)`. - All list/detail queries must be
workspace-scoped.

Ticket assignment was not part of the first core v1 scope. Update 2026-10-21
(owner decision): a nullable `assignee` (active member), assigned through
`POST tickets/{id}/assignee/` with the `tickets.assign` permission and the same
CLOSED-ticket ABAC lock as the protected fields. See `Project.MD`, Feature 5.

### 4.3 `TicketMessage`

**Purpose:** A single event/message in the ticket conversation,
including public replies and internal notes.

Fields: - `id`: UUID - `workspace_id` - `ticket_id` - `author_user_id`:
nullable for external customers - `author_type`: `AGENT`, `CUSTOMER`,
`SYSTEM`, `AI_DRAFT` - `visibility`: `PUBLIC` or `INTERNAL` -
`direction`: inbound, outbound, or internal - `body_text` -
`created_at`, `updated_at` - `email_message_id`: optional provider
message ID - `email_thread_id`: optional provider thread ID -
`in_reply_to`: optional RFC email Message-ID - `references_header`:
optional normalized reference metadata - `delivery_status`: optional
`QUEUED`, `SENT`, `FAILED`, `RECEIVED` - `sent_from_user_id`: nullable;
identifies the connected mailbox owner for outbound email -
`external_sender_email`: nullable

Rules: - Internal notes are never included in customer-facing API
responses or outgoing emails. - Customer-visible agent replies must be
persisted before being queued for email delivery. - Inbound email is
deduplicated by provider message ID and/or normalized message headers. -
Keep provider IDs for correlation, but do not make email the source of
truth for ticket history. - AI-generated content remains a draft until
an agent explicitly approves/sends it.

### 4.4 `TicketEvent`

**Purpose:** Structured audit/history for ticket changes.

Fields: - `id`, `workspace_id`, `ticket_id` - `actor_user_id`: nullable
for system/provider actions - `event_type`: status change, priority
change, category change, reply added, internal note added, email
delivery failure, etc. - `old_value`, `new_value`: optional JSON
fields - `created_at` - `metadata`: sanitized JSON, excluding secrets
and unnecessary email content

This record supports the activity timeline and auditing. Avoid
duplicating full message bodies in event metadata.

### 4.5 Customer follow-up (no access token)

**Decision (confirmed):** customers follow their ticket by email only.
There is no per-ticket access token and no customer ticket page. The
confirmation email links to the workspace portal, which opens the
new-ticket page. Customer replies arrive through the inbound Gmail flow
(section 7) and are matched by message headers.

### 4.6 Ticket categories (fixed)

**Decision (confirmed):** ticket categories are a fixed, code-defined
list (a `TicketCategory` `TextChoices` enum). There is no category model
and no per-workspace customization for tickets. The concrete values are
to be listed before implementation.

------------------------------------------------------------------------

## 5. Knowledge-base module

### 5.1 `KnowledgeArticle`

Fields: - `id`: UUID - `workspace_id` - `title` - `content` - `status`:
`DRAFT`, `PUBLISHED`, `ARCHIVED` - `created_by`, `updated_by` -
`created_at`, `updated_at`, `published_at` - `search_document`:
PostgreSQL `tsvector` field or equivalent database-managed search
representation, subject to the separate indexing design

Responsibilities: - Store workspace-owned articles. - Support
draft/published/archived lifecycle. - Only published articles are
eligible for AI retrieval. - Search must always be filtered by
`workspace_id` and published state. - Article content and citations must
never cross workspace boundaries.

**Content sources (confirmed):** articles are written in-app, and PDF
and TXT files can also be uploaded.

**Upload limit (confirmed):** 50 MB total per workspace
(`WORKSPACE_STORAGE_QUOTA_BYTES`). The quota is checked with an atomic
conditional update when an upload is reserved, and freed when the file
is deleted. Files go through `common.storage`.

Text extraction, chunking, and indexing for uploads are designed
together with the LLM layer (PostgreSQL full-text search, then Gemini),
which is built after the frontend and backend scaffolding.

### 5.2 `KnowledgeCategory` and `KnowledgeArticleCategory`

**Decision (confirmed):** knowledge categories are workspace-owned. New
workspaces start with a set of generic default categories, and users can
add, rename, and delete them. Use an explicit through model for
many-to-many assignment.

-   `KnowledgeCategory`: `id`, `workspace_id`, `name`, `slug`
-   `KnowledgeArticleCategory`: `article_id`, `category_id`

If v1 only needs one category per article, replace the through model
with a nullable FK.

### 5.3 Feedback (moved to AI)

Article-level `ArticleFeedback` is dropped. Feedback is given by signed-in
users on AI answers; see `AIFeedback` in 6.4a.

------------------------------------------------------------------------

## 6. AI module

### 6.1 `AIConversation`

**Purpose:** Conversation container for the standalone AI Assistant
page.

Fields: - `id` - `workspace_id` - `created_by_user_id` - `title`:
optional - `created_at`, `updated_at` - `is_archived`

Every access must validate current workspace membership. A conversation
must not be visible to users outside its workspace; conversations
are scoped per user per workspace (confirmed): only the creator can see
them. Sharing is out of scope for v1.

### 6.2 `AIMessage`

Fields: - `id` - `workspace_id` - `conversation_id` - `role`: `USER`,
`ASSISTANT`, `SYSTEM` (system content need not be persisted) -
`content` - `created_at` - `model_name`: optional - `request_id`:
optional correlation ID

Do not persist secrets or raw provider credentials. If full prompt
logging is enabled for debugging, it must be opt-in, sanitized,
access-controlled, and retention-limited; normal usage logs should not
require storing full prompts.

### 6.3 `AISource`

**Purpose:** Connect an AI answer to actual retrieved evidence.

Fields: - `id` - `workspace_id` - `ai_message_id` - `article_id` -
`article_title_snapshot`: optional - `excerpt`: short cited passage or
display snippet - `source_order` - `created_at`

Rules: - Sources must come from actual retrieval results, not
model-invented references. - Only cite published articles from the
active workspace. - Use stable article links and an excerpt/heading to
help the user verify the answer. - Validate article access when opening
a citation.

### 6.4a `AIFeedback`

Fields: `id`, `workspace_id`, `ai_message_id`, `user_id`, `rating`
(integer 1 to 5), `description` (optional, bounded length), `created_at`.
Unique `(ai_message_id, user_id)`. Feedback is user-scoped: only the user
who interacted with the AI can give it, and it is not shown publicly.

### 6.4 `AIUsageLog`

Fields: - `id` - `workspace_id` - `user_id` - `feature`: `ASSISTANT_QA`,
`DRAFT_REPLY`, `PARAPHRASE`, `TICKET_SUMMARY`, `CLASSIFICATION` -
`provider`: e.g. Gemini - `model_name` - `request_id` - `input_tokens`:
nullable - `output_tokens`: nullable - `latency_ms` - `status`:
`SUCCESS`, `ERROR`, `RATE_LIMITED`, `ABSTAINED` - `error_code`:
sanitized optional code - `created_at`

Purpose: - Track request counts, token usage where available, latency,
errors, and rate-limit events. - Do not show monetary cost as a metric
unless actual billable cost becomes applicable. - Do not store API keys
or sensitive customer content in usage logs.

### 6.5 AI service classes

**`KnowledgeRetrievalService`** -
`search_published_articles(workspace_id, query, limit)` -
`get_relevant_evidence(workspace_id, query, limit)` - Uses PostgreSQL
full-text search only in v1. - Enforces workspace and published-state
filters.

**`GeminiClient`** - `generate_answer(prompt, model, options)` -
`generate_structured_output(prompt, schema, options)` - Wraps provider
API errors, timeouts, and rate limits. - Reads the server-side API key
from environment/secret configuration.

**`CitationService`** -
`build_sources(retrieval_results, ai_response)` - Validates that
returned citations refer to retrieved articles. - Prefer
application-generated source IDs over trusting arbitrary URLs from the
model.

**`AIService`** -
`answer_question(user, workspace, conversation, question)` -
`draft_ticket_reply(user, workspace, ticket)` -
`paraphrase_reply(user, workspace, ticket, selected_text, instruction)` -
`summarize_ticket(user, workspace, ticket)` -
`suggest_category_and_priority(user, workspace, ticket)`

Responsibilities: 1. Validate membership and feature access. 2. Gather
only authorized ticket context and relevant published KB evidence. 3.
Abstain or ask for clarification if evidence is insufficient. 4. Call
Gemini with bounded context. 5. Validate the result and attach sources
from retrieved evidence. 6. Log usage and failures. 7. Return a
draft/suggestion; never send an email or change a ticket state
autonomously.

------------------------------------------------------------------------

## 7. Gmail integration module

### 7.1 Service classes

**`GoogleOAuthService`** - `verify_sign_in_callback(...)` -
`get_google_subject(identity_token)` - `create_session(user)` -
Validates OIDC state, nonce, issuer, audience, expiry, and signature
through a maintained OAuth/OIDC library.

**`GmailOAuthService`** - `start_authorization(user)` -
`complete_authorization(user, callback_data)` -
`verify_same_google_identity(user, gmail_identity)` -
`disconnect(user)` - Ensures the Gmail identity `sub` equals
`User.google_subject`.

**`GmailClient`** -
`send_message(connection, message, thread_metadata)` -
`get_message(connection, provider_message_id)` -
`list_history(connection, start_history_id)` -
`refresh_credentials(connection)` - Encapsulates Gmail API details and
provider errors.

**`TicketEmailService`** - `send_ticket_reply(ticket_message)` -
`send_ticket_confirmation(ticket)` - `send_delivery_failure_notice(...)`
if appropriate - Chooses the sender mailbox based on the authenticated
agent's connected Gmail account. - Sends only customer-visible messages;
internal notes must be rejected.

**`InboundEmailSyncService`** - `process_notification(payload)` -
`sync_mailbox(connection)` -
`ingest_message(connection, provider_message)` -
`match_message_to_ticket(provider_message)` -
`deduplicate_message(provider_message)` -
`record_unmatched_message(provider_message)`

Responsibilities: - Validate Pub/Sub push notifications (confirmed as
the primary mechanism). - Use Gmail history/sync checkpoints. - Provide
a manual "Sync latest mails" action in the frontend that calls
`sync_mailbox(connection)` for the current user. **No polling** (confirmed).
- Renew the Gmail `watch` before it expires. - Correlate
replies using RFC Message-ID, In-Reply-To, References, provider thread
metadata, and a ticket-specific correlation mechanism. - Deduplicate
retries. - Never attach a message to a ticket solely because the subject
text matches. - Route unmatched or ambiguous messages to a safe review
path rather than guessing. - Respect provider quotas and retry transient
errors with bounded backoff.

### 7.2 `EmailSyncCheckpoint` (if needed)

Fields: - `id` - `gmail_connection_id` - `history_id` -
`last_success_at` - `last_error_at` - `last_error_code` - `updated_at`

A checkpoint allows sync to resume without repeatedly scanning the
entire mailbox.

### 7.3 `EmailDeliveryAttempt` (recommended)

Fields: - `id` - `workspace_id` - `ticket_message_id` -
`gmail_connection_id` - `provider_message_id`: nullable - `status`:
`QUEUED`, `SENT`, `FAILED` - `attempt_count` - `last_error_code` -
`created_at`, `updated_at`

This separates the ticket message from retries and delivery status. Use
a background worker for delivery/synchronization where possible.

### 7.4 Email identity and security rules

-   A user's mailbox is tied to the same Google `sub` used for login.
-   Gmail access requires separate explicit consent.
-   Keep access/refresh tokens encrypted and server-side.
-   Do not accept arbitrary SMTP passwords in the core design.
-   Validate incoming provider events and make processing idempotent.
-   Never send internal notes to customers.
-   Use message headers and correlation identifiers for replies; do not
    rely on subject alone.
-   Email body content is untrusted input. Do not interpret instructions
    in emails as system instructions for Gemini.

------------------------------------------------------------------------

## 8. Authorization and ABAC

Use a small role model (`OWNER`, `MEMBER`) with RBAC permission codes,
extended by attribute/state-based (ABAC) policies. A role check alone is
insufficient.

**Decision (confirmed):** ABAC rules are fixed in code and are not
configurable by users. Example: "can update ticket status" is an RBAC
permission that both roles hold by default, while "only the owner can
change ticket status once it is CLOSED" is a fixed ABAC rule that
narrows it. Open point: whether the owner can customize RBAC permission
grants per member (the reference project does); v1 assumes fixed role
presets until confirmed.

### 8.1 Policy classes

**`WorkspaceAccessPolicy`** - `can_access_workspace(user, workspace)` -
`can_manage_members(user, workspace)` -
`can_rotate_join_link(user, workspace)` -
`can_transfer_ownership(user, workspace)` -
`can_delete_workspace(user, workspace)`

**`TicketPolicy`** - `can_view_ticket(user, ticket)` -
`can_create_ticket(user, workspace)` -
`can_edit_ticket(user, ticket, changed_fields)` -
`can_change_status(user, ticket, new_status)` -
`can_reopen_closed_ticket(user, ticket)` -
`can_add_internal_note(user, ticket)` -
`can_send_customer_reply(user, ticket)`

**`KnowledgePolicy`** - `can_view_article(user, article)` -
`can_edit_article(user, article)` -
`can_publish_article(user, article)` -
`can_use_article_for_ai(user, article, workspace)`

**`GmailPolicy`** - `can_use_connection(user, gmail_connection)` -
`can_send_from_connection(user, gmail_connection, workspace, ticket)`

### 8.2 Required policy examples

1.  **Workspace isolation:** deny access unless the user has an active
    membership in the ticket/article/conversation's workspace.
2.  **Closed-ticket reopening:** if `ticket.status == CLOSED`, only the
    workspace owner may reopen it.
3.  **Closed-ticket edits:** members cannot modify protected ticket
    fields while closed; owner may reopen and then edit, subject to
    policy.
4.  **Public customer access:** anonymous customers can only submit
    tickets through the portal; they have no read access to tickets.
5.  **Internal-note protection:** internal messages are visible only to
    authorized workspace members and never sent to the customer.
6.  **Knowledge retrieval:** AI may retrieve only published articles
    belonging to the active workspace.
7.  **Gmail sender identity:** an agent can send only through their own
    active Gmail connection; the connection's Google subject must match
    the user's login identity.
8.  **Ownership transfer:** only the current owner may transfer
    ownership; the transfer must preserve one active owner.
9.  **Account deletion:** deny deletion if the user still owns any
    workspace without first transferring ownership.
10. **Membership revocation:** a removed member loses future access even
    if they know a previous workspace or ticket URL.

### 8.3 Enforcement pattern

-   Enforce policies in service methods and DRF permissions/querysets.
-   Filter querysets by authorized workspace before fetching individual
    records.
-   Do not rely on UUIDs, hidden UI controls, or unguessable URLs as
    substitutes for authorization.
-   Add negative tests for cross-workspace access and state-transition
    violations.
-   Record sensitive administrative actions in `AuditEvent`.

------------------------------------------------------------------------

## 9. Accounts, sessions, and audit

### 9.1 Session handling

Django server-side sessions should use secure cookie settings in
production: - `Secure`, `HttpOnly`, and appropriate `SameSite` cookie
policy. - CSRF protection for state-changing requests. - HTTPS only. -
Session rotation after authentication and privilege changes. -
Idle/absolute expiry policy. - **In v1 (confirmed):** a "remember me"
option, a session list with per-device revoke (log out of one device),
and log out of all devices. This needs a `UserSession` record per login
alongside the Django session.

### 9.2 `AuditEvent`

Fields: - `id` - `workspace_id`: nullable for account-level events -
`actor_user_id`: nullable for system events - `action` - `target_type`,
`target_id` - `created_at` - `ip_hash` or limited security metadata only
if justified - `metadata`: sanitized JSON

Examples: - ownership transferred - member joined or removed - join link
rotated - ticket closed/reopened - knowledge article published - Gmail
connection added/disconnected - account deletion initiated/completed

Do not store OAuth tokens, raw join tokens, customer ticket access
tokens, or unnecessary message bodies in audit metadata.

------------------------------------------------------------------------

## 10. Dashboard read models

Dashboard queries should be workspace-scoped and derived from canonical
records.

Suggested service: **`DashboardService`** -
`get_ticket_counts(workspace, period)` -
`get_ticket_volume(workspace, period)` -
`get_recent_activity(workspace, limit)` -
`get_waiting_for_reply_tickets(workspace, limit)` -
`get_most_used_articles(workspace, period)` -
`get_ai_usage_summary(workspace, period)`

Metrics: - open and urgent tickets - resolved tickets over a selected
period - ticket volume over time - recently updated tickets - tickets
waiting for a reply (definition: the last public message was sent by the
customer, so the ticket awaits an agent; owner's wording was "sent by the
user", confirm) -
recent workspace activity - most-used KB articles - AI request counts,
tokens where available, errors, and rate-limit events

Implemented (v1): a single read endpoint `GET /api/workspaces/{id}/dashboard/`
covering the ticket metrics above (see `docs/DASHBOARD_API.md`); most-used
articles and AI usage wait for the AI phase.

Do not claim SLA compliance or average response time until the metric
definitions and required timestamps are agreed.

------------------------------------------------------------------------

## 11. API/service boundary sketch

These are logical service operations, not a final URL specification.

  ------------------------------------------------------------------------------------
  Area                    Operation                    Main service
  ----------------------- ---------------------------- -------------------------------
  Auth                    Google OAuth callback        `GoogleOAuthService`

  Account                 profile update / account     `AccountService`
                          deletion                     

  Workspace               create/update workspace      `WorkspaceService`

  Workspace               redeem/rotate join link      `WorkspaceJoinService`

  Workspace               transfer ownership           `WorkspaceService`

  Gmail                   connect/disconnect mailbox   `GmailOAuthService`

  Ticket                  public ticket submission     `TicketService`

  Ticket                  list/detail/update           `TicketService` +
                                                       `TicketPolicy`

  Ticket                  add internal note            `TicketMessageService` +
                                                       `TicketPolicy`

  Ticket                  send customer reply          `TicketReplyService` +
                                                       `GmailPolicy`

  Knowledge               CRUD/publish article         `KnowledgeArticleService` +
                                                       `KnowledgePolicy`

  Knowledge               search published articles    `KnowledgeRetrievalService`

  AI                      standalone assistant Q&A     `AIService`

  AI                      draft/paraphrase/summarize   `AIService`

  Email                   inbound sync event           `InboundEmailSyncService`

  Dashboard               metrics                      `DashboardService`
  ------------------------------------------------------------------------------------

API views/serializers should validate input and format output; they
should not contain large business workflows.

------------------------------------------------------------------------

## 12. Important workflows

### 12.1 Google login

1.  User starts Google OIDC flow.
2.  Backend validates state/nonce and verifies identity claims.
3.  Backend finds or creates `User` using the stable Google `sub`.
4.  Backend rotates/creates the server-side session.
5.  Browser receives only the session cookie, not OAuth provider tokens.

### 12.2 Connect Gmail

1.  Authenticated user starts Gmail authorization.
2.  Backend requests only necessary Gmail scopes.
3.  Callback is validated; Gmail identity is resolved.
4.  Backend rejects the connection if Gmail
    `sub != User.google_subject`.
5.  Refresh token is encrypted and saved to `GmailConnection`.
6.  Connection status and sync checkpoint are initialized.

### 12.3 Public ticket creation

1.  Customer opens the workspace's public portal.
2.  Backend resolves the workspace by public slug and validates portal
    settings.
3.  Customer submits a subject, description, and required email.
4.  Backend validates and rate-limits the request, creates the ticket
    and initial public message, and, since follow-up is by email only, creates no customer token.
5.  A confirmation email is queued; it links to the portal.
6.  No internal workspace data is returned to the anonymous customer.

### 12.4 Agent reply

1.  Backend verifies active workspace membership and ticket access.
2.  `TicketPolicy` checks ticket state and requested action.
3.  Public reply is stored as a `TicketMessage`.
4.  An email delivery attempt is queued using the authenticated agent's
    Gmail connection.
5.  Delivery status is updated; retries are idempotent.
6.  The ticket activity timeline records the action.

### 12.5 AI-assisted reply

1.  Validate user membership and ticket access.
2.  Retrieve only relevant published KB evidence from the same
    workspace.
3.  Construct bounded context from the ticket and retrieved evidence.
4.  Call Gemini through `GeminiClient`.
5.  Validate output and attach sources only from actual retrieval
    results.
6.  Return an editable draft and evidence to the agent.
7.  The agent edits/approves and explicitly sends; AI does not send
    autonomously.

### 12.6 Inbound Gmail reply

1.  Receive a Pub/Sub push notification, or the user presses "Sync latest mails".
2.  Validate the event and load the correct user's `GmailConnection`.
3.  Fetch new messages from the Gmail API.
4.  Deduplicate and match using message headers and correlation
    metadata.
5.  If confidently matched, create a customer-visible inbound
    `TicketMessage` and update ticket activity.
6.  If unmatched or ambiguous, route to review rather than attach by
    subject alone.

------------------------------------------------------------------------

## 13. Core v1 vs stretch boundary

### Core v1

-   Google-only authentication and server-side sessions.
-   One Gmail connection per user, restricted to the same Google
    identity.
-   Multiple workspaces per user; owner/member membership; ownership
    transfer.
-   Revocable/rotatable join link with direct membership.
-   Workspace-scoped ticket CRUD, filtering/search,
    status/priority/category, chronological messages.
-   Public ticket submission with required customer email.
-   Public replies vs internal notes with strict separation.
-   Gmail API send flow and inbound sync (Pub/Sub push plus a manual
    sync button; no polling).
-   "Remember me", per-device session list and revoke, log out of all
    devices.
-   Knowledge articles created/edited in-app, draft/published/archived
    states, and PDF/TXT uploads with a 50 MB per-workspace limit
    (extraction and indexing built with the LLM layer).
-   PostgreSQL full-text search over published articles.
-   AI Assistant Q&A with citations, and 1 to 5 star AI feedback.
-   AI ticket reply drafts, paraphrasing, ticket summaries,
    category/priority suggestions.
-   AI usage/error/rate-limit logging.
-   Backend-enforced workspace isolation and ABAC rules.
-   Audit events for sensitive actions.

### Stretch / defer unless explicitly required

-   DOCX and other upload formats beyond PDF/TXT.
-   Vector embeddings or vector search.
-   Assignment-based policies beyond the basic assignee (built 2026-10-21).
-   Multiple Gmail mailboxes per user.
-   SMTP credentials and non-Google mail providers.
-   Advanced analytics, SLA dashboards, automated workflows.
-   Shared AI conversations, unless explicitly requested.
-   Automatic AI sending or autonomous ticket status changes (not
    recommended for v1).

------------------------------------------------------------------------

## 14. Decisions

### Confirmed by the owner (2026-10-16)

1.  `RESOLVED` and `CLOSED` stay separate; owner-only reopening.
2.  Workspace slug is immutable.
3.  Customer follow-up is email only; no customer access token.
4.  Knowledge base: in-app articles plus PDF/TXT uploads; 50 MB per
    workspace; ingestion designed with the LLM layer.
5.  AI conversations are private per user per workspace.
6.  Ticket categories are fixed; knowledge categories ship with defaults
    and are user-editable.
7.  Inbound Gmail via Pub/Sub push plus a manual sync button; no polling.
8.  AI feedback is a 1 to 5 star rating with an optional description,
    user-scoped.
9.  ABAC rules are fixed and not configurable; they extend RBAC.
10. Remember me, session list/revoke, and log out of all devices are in v1.
11. Build order: reusable `common` app, then frontend and backend, then
    PostgreSQL full-text search and Gemini.

### Still open

-   The concrete list of fixed ticket categories and the default
    knowledge categories.
-   Whether the owner can customize RBAC permission grants per member.
-   "Waiting for reply" wording (assumed: last public message is from the
    customer).
-   Gmail Pub/Sub prerequisites: Google Cloud project, topic and push
    endpoint, OAuth verification for Gmail scopes, quotas.
-   Ticket status transition rules and the portal enable/disable setting.

------------------------------------------------------------------------

## 15. Cross-cutting implementation rules

-   Use UUID primary keys for externally exposed records.
-   Use database constraints for uniqueness and referential integrity
    wherever possible.
-   Use transactions for ownership transfer, membership changes, and
    state transitions.
-   Use idempotency/deduplication for inbound email and outbound
    delivery retries.
-   Keep secrets in environment-backed secret configuration; never
    commit them.
-   Validate uploaded file types and sizes if file uploads are added
    later.
-   Sanitize rendered customer/agent content against XSS.
-   Rate-limit public ticket submission, join-link redemption,
    customer-token access, and AI calls.
-   Add tests for unauthorized cross-workspace reads/writes,
    internal-note leakage, wrong-Google-account Gmail connection,
    duplicate inbound messages, and owner-only reopening.
-   Keep timestamps in UTC in storage and convert for display.
-   Do not log access tokens, raw one-time tokens, API keys, or
    sensitive message contents.
