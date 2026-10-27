# FLOW.md

How code travels between files and functions. Update the relevant flow whenever a call path changes. References are `path::name`.

## 1. Any API request (implemented)

1. `common/logger/request_id.py::RequestIdMiddleware` assigns/accepts `X-Request-ID`, stores it in a context var, echoes it on the response.
2. Django session + auth middleware; `common/logger/request_id.py::UserContextMiddleware` records the user id for logs/Sentry.
3. `common/logger/middleware.py::RequestLoggingMiddleware` wraps the view; it logs method, route, redacted headers/body (`common/logger/redaction.py::redact_sensitive_data`), status and duration.
4. DRF throttles (`common/throttling/scoped.py::AnonThrottle`, `UserThrottle`, `WorkspaceThrottle`, plus per-view `AuthScopedThrottle` scopes from `config/settings.py::THROTTLE_RATES`).
5. View -> `Serializer.parse(request.data)` (`common/serializers/base.py::StrictSerializer.parse`) -> service function (business logic) -> `SuccessResponse` (`common/response/domain.py`).
6. Errors: services raise `common/exception/domain.py::AppException` subclasses; DRF validation/auth/throttle errors are mapped in `common/exception/handler.py::exception_handler` (strategy list of `BaseExceptionHandler`s) into `ErrorResponse`. Unknown exceptions fall through to a normal 500 (and Sentry via `common/observability/sentry.py::before_send`).

Health check: `config/urls.py` -> `common/urls.py` -> `common/views.py::HealthView.get` -> `SuccessResponse`.

## 2. File storage (implemented)

Caller -> `common/storage/__init__.py::get_storage()` (R2 if `R2_BUCKET_NAME`, else local disk) -> `FileStorage` methods in `common/storage/base.py`. Tests use `common/storage/memory.py::InMemoryStorage`.

## 3. Secrets at rest (implemented)

Service -> `common/crypto.py::encrypt/decrypt/rotate` using `settings.ENCRYPTION_KEYS`. Used later for `GmailConnection.encrypted_refresh_token`.

## 4. Caching (implemented)

`CacheModel.save/delete` and `SoftDeleteQuerySet.delete` -> `common/cache/manager.py::cache_manager` invalidate keys built by `keys_for`.

## 5. Google sign-in (implemented)

1. Browser -> `GET /api/auth/google/start/?remember=&next=` -> `accounts/views/google.py::GoogleStartView.get` (throttled `google` scope; throttled requests redirect with `google_error=rate_limited`). It stores the remember flag and a validated same-site `next` path in the session (`accounts/redirects.py::is_safe_next_path`), removes `next` from the request, and calls allauth's `oauth2_login`, which redirects to Google (PKCE, `state` in the session).
2. Google -> `GET /api/auth/google/login/callback/` -> `GoogleCallbackView.get` (same throttles) -> allauth `oauth2_callback`: checks `state`, exchanges the code, validates the ID token.
3. `accounts/adapters.py::SocialAccountAdapter.pre_social_login` rejects unverified email, inactive users and an email already held by another account (no linking by email); refreshes the avatar of a returning user. A new user is created by allauth auto-signup using `SocialAccountAdapter.populate_user`.
4. `AccountAdapter.login` logs in (session key rotates) and sets expiry: 30 days with remember me, else 14 days. The `user_logged_in` signal runs `accounts/signals.py::on_user_logged_in` -> `services/deletion_service.py::cancel_deletion` and emits the audit event.
5. `AccountAdapter.get_login_redirect_url` / `get_signup_redirect_url` redirect to `FRONTEND_URL` + `next` or `/app`. Any failure goes through `SocialAccountAdapter.on_authentication_error` to `FRONTEND_URL/?google_error=<code>` (the landing page shows the message).

## 6. Sessions and profile (implemented)

`/api/auth/sessions/` and `/api/auth/logout*` -> `accounts/views/session.py` -> `services/session_service.py` (allauth `UserSession` rows are created per authenticated request by `UserSessionsMiddleware`; `device.py::device_label` parses the user agent). `/api/me/` -> `views/profile.py::MeView` -> `profile_service.update_display_name` or `deletion_service.request_deletion` (runs `hooks.ownership_checks`, sets `deletion_requested_at`, ends all sessions). Daily beat tasks in `accounts/tasks.py` purge accounts past the 7-day grace and expired sessions.

## 7. Workspaces (implemented)

Every `/api/workspaces/{workspace_id}/...` request: view -> `workspaces/services/access.py::get_membership` (ACTIVE membership in a live workspace, else 404) or `require_permission` (RBAC code from `workspaces/constants/permissions.py::ROLE_PERMISSIONS`, else 403) -> service. `WorkspaceThrottle` caps all traffic per `workspace_id`.

- **Create:** `views/workspace.py::WorkspaceListView.post` -> `workspace_service.create_workspace` (slug derived or validated, workspace and OWNER membership in one transaction) -> `hooks.emit`.
- **Join link:** owner `JoinLinkView.post` -> `join_link_service.rotate_link` (revokes the live link, stores only `hash_token`, returns the raw token once). Anyone signed in: `RedeemJoinLinkView.post` (`IPScopedThrottle` scope `join_link`) -> `join_link_service.redeem` -> `member_service.add_member` (creates or re-activates a MEMBER).
- **Invitation:** owner `WorkspaceInvitationListView.post` -> `invitation_service.create_invitations` (`common/email/utils.py::canonical_email_key` dedupes mailboxes). Invitee: `MyInvitationListView.get` lists by the canonical key of their sign-in email; `AcceptInvitationView.post` -> `invitation_service.accept_invitation` (atomic claim, then `add_member`).
- **Ownership transfer:** `TransferOwnershipView.post` -> `member_service.transfer_ownership` (row locks, demote then promote in one transaction).
- **Delete and purge:** `WorkspaceDetailView.delete` -> `workspace_service.delete_workspace` (soft delete). Beat task `workspaces/tasks.py::purge_deleted_workspaces` -> `workspace_service.purge_due_workspaces` (hard delete and logo removal after 7 days).
- **Logo:** `LogoUploadUrlView.post` -> `logo_service.create_upload_url` (signed PUT via `common/storage`) -> browser PUT to R2 -> `LogoView.put` -> `logo_service.confirm_logo` (checks the object exists, type and size, then swaps and deletes the old object).
- **Account deletion check:** `workspaces/apps.py::ready` registers `services/ownership.py::account_ownership_blocker` with `accounts.services.hooks`, which `accounts/services/deletion_service.py::request_deletion` runs.

## 8. Knowledge base (implemented)

All routes: `/api/workspaces/{workspace_id}/knowledge/...` -> `workspaces/services/access.py::require_permission` (`KNOWLEDGE_VIEW` / `KNOWLEDGE_MANAGE`, 404 for non-members) -> service.

- **Article write:** `views/article.py::ArticleListView.post` / `ArticleDetailView.patch` -> `services/article_service.py::create_article` / `update_article` -> one transaction: `quota_service.reserve` (conditional UPDATE on `Workspace.storage_used_bytes`), row with `content`, categories, and `chunk_service.rebuild_chunks` when the title or content changed. `KnowledgePolicy.ensure_can_edit` blocks archived articles. (Uploaded files still go to R2, see Upload.)
- **Article read:** `ArticleDetailView.get` -> the row's `content`. Lists use `article_service.list_articles` (database filters only).
- **Status:** `PublishArticleView` / `UnpublishArticleView` / `ArchiveArticleView` -> `article_service.change_status` (allowed transitions table).
- **Delete:** `article_service.delete_article` -> row (and its chunks) removed and `quota_service.release` in the transaction.
- **Upload:** `UploadUrlView.post` -> `upload_service.create_upload` (checks `category_id` belongs to the workspace, reserves quota, PENDING row filed under the category, signed PUT) -> browser PUT to R2 -> `UploadConfirmView.post` -> `upload_service.confirm_upload` (HEAD size and type, PDF magic bytes, DOCX zip structure; a bad object is discarded and its quota released) -> `transaction.on_commit` -> Celery `knowledge/tasks.py::index_upload` on the `documents` queue -> `upload_index_service.index_upload` (see Upload indexing below). `UploadDownloadView.get` -> `upload_service.download_url` (signed GET, forced download). Hourly `knowledge/tasks.py::release_stale_uploads` -> `upload_service.release_stale_uploads`.
- **Workspace lifecycle:** `knowledge/signals.py::on_workspace_event` seeds the default categories on `workspace.created` and deletes stored objects on `workspace.purged` (`workspaces/services/hooks.py::workspace_event`).

## 9. Tickets and public portal (implemented)

- **Agent routes** `/api/workspaces/{workspace_id}/tickets/...` -> `workspaces/services/access.py::require_permission` (`TICKETS_VIEW` / `TICKETS_MANAGE`, 404 for non-members) -> `tickets/services/ticket_service.py` or `message_service.py`; ABAC rules in `tickets/policies.py::TicketPolicy`.
- **Create (agent or portal):** `ticket_service.create_ticket` -> one transaction: `numbering.next_ticket_number` (row-locking counter on the workspace), `Ticket`, the customer's first `TicketMessage`, a `created` `TicketEvent` -> `hooks.emit`.
- **Status:** `TicketStatusView.post` -> `ticket_service.change_status` (row lock, `TicketPolicy.ensure_can_change_status`, resolved/closed timestamps, event).
- **Assign:** `TicketAssigneeView.post` -> `AssignTicketSerializer` -> `ticket_service.assign_ticket` (`TICKETS_ASSIGN`, row lock, `TicketPolicy.ensure_can_change_assignee`, active-membership check, `assignee_changed` event, `hooks.emit` `ticket.assignee_changed`). Leaving or removal: `member_service.remove_member` / `leave_workspace` -> `workspace_event` -> `tickets/signals.py::unassign_departed_member` -> `ticket_service.unassign_departed_member`. List filter `assignee` (`me`, `unassigned`, user id) is applied in `ticket_service.list_tickets`.
- **Update:** `TicketDetailView.patch` -> `ticket_service.update_ticket` (`TicketPolicy.ensure_can_edit` for closed tickets, one event per change type).
- **Reply or note:** `TicketMessageListView.post` -> `message_service.add_message` (public reply: `ensure_can_reply`, stored QUEUED with `sent_from_user`, feature 6 will send it; note: internal) -> event without the body.
- **Ticket page in one call:** `views/ticket.py::TicketOverviewView.get` -> `services/overview_service.py::build` (permission check through `ticket_service.get_for_user`, the viewer's membership role and `ROLE_PERMISSIONS`, the newest messages and events, then each registered extra block; `email_integration/apps.py::ready` registers `services/overview.py::gmail_status_block`).
- **Portal:** `views/portal.py::PortalTicketView.post` (no auth, `IPScopedThrottle` scope `portal_ticket`) -> `PortalTicketSerializer` -> `portal_service.submit` (workspace by slug and `portal_enabled`, honeypot check, per-email cache counter, then `ticket_service.create_ticket` with source portal and `confirmation_pending`). `PortalInfoView.get` -> `portal_service.portal_info`.

## 10. Gmail and email (implemented)

- **Grant at sign-in:** Google callback (section 5) -> allauth `user_logged_in` (with `sociallogin`) -> `email_integration/signals.py::record_gmail_grant` -> `services/connection_service.py::record_login_grant` (tokeninfo for granted scopes, `token_service.encrypt_refresh_token`, `GmailConnection`) -> task `ensure_gmail_watch` when a Pub/Sub topic is configured.
- **Reply out:** `tickets/services/message_service.py::add_message` emits `ticket_signal` (reply added, with the message id) -> `email_integration/signals.py::on_ticket_event` -> after commit `tasks.send_ticket_message` -> `services/send_service.py::send_ticket_message` -> `mime_service.build_reply` -> `clients.get_gmail_client(...).send` -> read back the sent message -> store Message-ID/thread id, `sent`, or `failed` with a `delivery_error` and an event.
- **Invitation email:** `invitation_service.create_invitations` -> `hooks.emit_invitations_created` -> `email_integration/signals.py::on_invitations_created` -> after commit `tasks.send_invitation_email` -> `send_service.send_invitation_email` (inviter's Gmail through `mime_service.build_reply`; skipped and logged without raising when Gmail is missing or fails; sets `notified_at`).
- **Portal confirmation:** `ticket_signal` (created, source portal) -> `tasks.send_portal_confirmation` -> `send_service.send_portal_confirmation` (owner's mailbox, stored as a system message).
- **Mail in:** Pub/Sub -> `views/gmail.py::GmailPushView` (`push_service.verify_request`) -> `tasks.sync_mailbox` -> `inbound_service.sync_from_history`; the button -> `GmailSyncView` -> `inbound_service.manual_sync`. Both end in `inbound_service.process_message`: ignore own/sent mail, dedupe by Message-ID, match by `In-Reply-To`/`References` plus sender check -> `_store_customer_reply`, else known customer -> `_store_for_review`, else ignore.
- **Review:** `ReviewAttachView` -> `review_service.attach_to_ticket` (fetches the body again); `ReviewDismissView` -> `dismiss`. Daily `purge_old_review_items`.
- **Disconnect:** `GmailStatusView.delete` -> `connection_service.disconnect` (stop watch, revoke, wipe token).

## 11. Audit log (implemented)

- **Recording:** a service emits its hook signal (`workspaces/services/hooks.py::emit`, `knowledge/services/hooks.py::emit`, `tickets/services/hooks.py::emit`, `accounts/services/hooks.py::emit`, `email_integration/services/hooks.py::emit`) -> `audit/signals.py` receiver -> `constants/actions.py::ACTIONS` (is it registered, what is the target, is it account-level) -> `services/recorder.py::record` -> `services/sanitize.py::sanitize_metadata` -> `AuditEvent` row. Any failure is logged and swallowed.
- **Reading:** `audit/views/events.py::AuditEventListView.get` -> `AuditFilterSerializer` -> `services/list_service.py::list_events` (`workspaces/services/access.py::require_permission` with `AUDIT_VIEW`, owner only) -> paginated list, newest first.

## 12. Dashboard (implemented, inside the `audit` app)

- **Read:** `audit/views/dashboard.py::DashboardView.get` (throttles `UserThrottle`, `WorkspaceThrottle`, scope `dashboard`) -> `serializers/dashboard_requests.py::DashboardQuerySerializer.parse` (unknown, blank or invalid parameters -> 400) -> `audit/services/dashboard_service.py::get_dashboard`: `workspaces/services/access.py::require_permission` with `DASHBOARD_VIEW` (404 for non-members) -> `services/dashboard_period.py::resolve` (window and previous window in the requested time zone) -> `common/cache/manager.py::get_or_set` (30 s, key from workspace, dates, tz, sections, limits) -> on a miss `_build` -> `services/dashboard_metrics.py::summary`, `volume`, `recent_tickets`, `waiting_tickets`, `activity` -> item builders in `serializers/dashboard_responses.py` -> `DashboardData` in a `SuccessResponse` with `meta.cached`.
- **`resolved_at`:** `tickets/services/ticket_service.py::change_status` sets it on the first entry to resolved or closed and clears it when the ticket returns to open, in progress or pending.

## 13. Context search (implemented)

- **Settings:** `ai/views/settings.py::LLMSettingsView` (GET/PATCH, scope `llm_settings`) and `LLMKeyView.delete` -> `ai/services/settings_service.py` (permission `ai.use`, key validated by `common/llm` `validate_key`, encrypted by `key_vault` with `common/crypto.py`) -> `ai/services/hooks.py` audit events. `ai/signals.py` deletes the key when a member leaves or is removed.
- **Chat question:** `knowledge/views/context.py::ContextView.post` (scope `ai`) -> `ContextQuestionSerializer` -> `knowledge/services/context_service.py::retrieve_for_question` -> `retrieve_context`.
- **Ask:** `knowledge/views/context.py::AskView.post` (scope `ai`) -> `knowledge/services/answer_service.py::answer_question` -> `retrieve_for_question` -> no passages: `no_results`; otherwise `llm_service.generate` with the numbered passages -> `parse_answer` (valid `[n]` only) -> `AnswerData` (`status`, `answer`, `cited` plus the context fields). An LLM error returns `unavailable` with the passages.
- **Ask history:** `answer_service.answer_question` first calls `ask_history.check_can_add_turn` (own chat, under the turn cap), then answers, then `ask_history.record_turn` stores question and payload (`answer_payload`) and returns the ids. `AskConversationListView`, `AskConversationDetailView` (GET, DELETE) read and delete only the caller's chats. `knowledge/signals.py` deletes a member's chats when they leave or are removed.
- **Ticket customer message:** no ticket endpoint. The ticket page sends the raw message to the Ask page (`/app/{ws}/ask?q=...`), which starts a new chat through `AskView`.
- **`retrieve_context`:** `common/search/context.py::context_query` (stemmed OR terms, 12-term cap) -> `rewrite_service` (cached 1 h; `llm_service.generate` -> `allowance` check for the Resolve AI key -> `common/llm` provider; any failure returns no rewrites) -> `_ranked` per query (`common/search/query.py::search_with_query` over PUBLISHED chunks of the workspace, `ts_rank_cd`, score floor) -> `_merge` (reciprocal rank fusion) -> top 5 (no per-article limit) -> `with_headline` for those rows -> `ContextData` (`terms`, `queries`, `rewritten`, `results`).
- **BM25 word search:** `context_service._ranked` -> `context_service._bm25_ranked` (ParadeDB `bm25_terms ||| terms`, `pdb.score`, workspace and published/ready filter; `DatabaseError` -> old `ts_rank_cd` path). `bm25_terms` is written by `chunk_service.fill_vectors` (`BM25_TERMS_SQL`) next to `search_vector`.
- **Hybrid search (articles and uploaded files):** `retrieve_context` also embeds the original text and the rewrites in one request (`embedding_service.embed_queries` -> `common/llm` `embed`, Resolve AI key, 300 searches per user per day) and runs `_vector_rankings` (pgvector `CosineDistance` over `embedding`, similarity >= 0.55, HNSW with `hnsw.iterative_scan`) next to `_ranked` for each query; `_merge` fuses all lists, the top 5 are kept (no per-article or per-file limit). `_visible_chunks` = chunks of PUBLISHED articles or READY uploads. No embedding (error, limit, no key, SQLite) means words only.
- **Upload indexing (PDF headings and line cuts):** `common/documents/pdf_parser.py::_page_text` turns large-font short lines into `#` headings; `chunker._split_document_lines` cuts long document blocks between lines.
- **Upload indexing:** `index_upload` -> `upload_index_service.index_upload` (INDEXING, read the original from storage, `common/documents` parser: pdfplumber for PDF, python-docx for DOCX, plain read for TXT/MD, page cap and timeout) -> store the Markdown as `<upload>.extracted.md` -> `chunk_service.upload_drafts` -> `rebuild_upload_chunks` (incremental, one transaction with INDEXED). Errors from the parser mark the upload FAILED with a code; unexpected errors retry twice with backoff, then FAILED. Beat `knowledge.requeue_unindexed_uploads` (every 10 min) re-queues lost or abandoned runs. `reindex_knowledge --uploads` queues every READY upload with `force`.
- **Embedding:** `chunk_service._sync` -> `on_commit` -> `knowledge/tasks.py::embed_source(kind, id)` -> `embedding_service.embed_source` (chunks with no vector or another `embedding_model`, batches of 100, daily per-workspace chunk cap in the cache) -> `bulk_update`. Rate limits and timeouts retry 3 times; beat `knowledge.embed_pending_chunks` (every 15 min) covers the rest. `reindex_knowledge --embeddings` clears the vectors.
- **Index upkeep:** `knowledge/services/chunk_service.py::rebuild_chunks` on article create and on edits; `reindex_knowledge` command; a `search_language` change queues a Celery reindex.

## 13b. Ticket summary and draft reply (implemented)

- **Summary:** `tickets/views/ai.py::TicketSummaryView.post` (scope `ai`) -> `tickets/services/ai_service.py::summarize` -> public messages only -> `llm_service.generate`. Not stored.
- **Draft reply:** `TicketDraftReplyView.post` -> `DraftReplySerializer` (`intent`, required, max 200) -> `ai_service.draft_reply` -> public conversation + `retrieve_context` passages -> `llm_service.generate` with the user's name as signature -> `draft` and `sources`. Not sent, not stored.
- **Frontend:** `features/tickets/ai-actions.tsx`, `ai-api.ts`.

## 14. Planned flows (not implemented yet; see the LLD, section 12)

Mark each as implemented, with real file references, when built: none at the moment.
