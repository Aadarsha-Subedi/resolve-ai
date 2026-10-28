"""The AI usage log: every AI call in a workspace (answered from the cache, sent to the
provider, or failed), readable by the workspace owner only.

Writing a row never breaks the call it describes: any database error is logged and dropped."""

import logging
from datetime import timedelta

from django.db import models
from django.db.models import F, Q, QuerySet
from django.utils import timezone

from accounts.models import User
from ai.constants import settings as cfg
from ai.models import AIUsageLog
from common.llm.constants import ALLOWED_MODELS, RESOLVE_AI_MODELS
from workspaces.constants import permissions
from workspaces.services import access

logger = logging.getLogger(__name__)


def provider_of(model: str) -> str:
    """The provider a model name belongs to ('' when unknown)."""
    if model in RESOLVE_AI_MODELS:
        return "gemini"
    return next(
        (name for name, models_ in ALLOWED_MODELS.items() if model in models_), ""
    )


def record(
    workspace_id,
    user_id,
    feature: str,
    outcome: str,
    *,
    question: str = "",
    answer: str = "",
    provider: str = "",
    model: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    error_code: str = "",
    details: dict | None = None,
) -> None:
    try:
        AIUsageLog.objects.create(
            workspace_id=workspace_id,
            user_id=user_id,
            feature=feature,
            outcome=outcome,
            provider=provider,
            model=model,
            question=question,
            answer=answer,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error_code=error_code[: cfg.USAGE_ERROR_MAX_LENGTH],
            details=details or {},
        )
    except Exception:
        logger.warning("AI usage log row not saved", exc_info=True)


def list_logs(
    user: User,
    workspace_id,
    *,
    search: str | None = None,
    feature: str | None = None,
    outcome: str | None = None,
    actor=None,
    created_from=None,
    created_to=None,
    ordering: str = "-created_at",
) -> QuerySet[AIUsageLog]:
    """The workspace's usage log. Owner only (404 for non-members, 403 for members)."""
    access.require_permission(user, workspace_id, permissions.AI_USAGE_VIEW)
    queryset = AIUsageLog.objects.filter(workspace_id=workspace_id)
    if search:
        queryset = queryset.filter(
            Q(question__icontains=search)
            | Q(answer__icontains=search)
            | Q(user__display_name__icontains=search)
            | Q(user__email__icontains=search)
        )
    if feature:
        queryset = queryset.filter(feature=feature)
    if outcome:
        queryset = queryset.filter(outcome=outcome)
    if actor:
        queryset = queryset.filter(user_id=actor)
    if created_from:
        queryset = queryset.filter(created_at__date__gte=created_from)
    if created_to:
        queryset = queryset.filter(created_at__date__lte=created_to)
    descending = ordering.startswith("-")
    field = cfg.USAGE_ORDERINGS[ordering.lstrip("-")]
    queryset = queryset.annotate(
        total_tokens=models.F("input_tokens") + models.F("output_tokens")
    )
    key = F(field).desc() if descending else F(field).asc()
    return queryset.select_related("user").order_by(key, "-id")


def summary(queryset: QuerySet[AIUsageLog]) -> dict:
    """Counts for the filtered log: calls, answered from the cache, sent to the provider."""
    counts = queryset.order_by().aggregate(
        total=models.Count("pk"),
        cache_hits=models.Count("pk", filter=Q(outcome=cfg.USAGE_OUTCOME_CACHE_HIT)),
        llm_calls=models.Count("pk", filter=Q(outcome=cfg.USAGE_OUTCOME_LLM_CALL)),
        errors=models.Count("pk", filter=Q(outcome=cfg.USAGE_OUTCOME_ERROR)),
    )
    answered = counts["cache_hits"] + counts["llm_calls"]
    counts["hit_rate"] = round(counts["cache_hits"] / answered, 4) if answered else None
    return counts


def purge_old() -> int:
    cutoff = timezone.now() - timedelta(days=cfg.USAGE_RETENTION_DAYS)
    deleted, _ = AIUsageLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted
