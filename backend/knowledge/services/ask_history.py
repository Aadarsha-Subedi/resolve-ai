"""Chat history of the Ask page: private conversations, one user in one workspace."""

from django.db import transaction
from django.db.models import Count

from accounts.models import User
from common.exception.domain import ConflictException, NotFoundException
from knowledge.constants import errors, messages
from knowledge.constants import settings as cfg
from knowledge.models import AskConversation, AskTurn
from workspaces.constants import permissions
from workspaces.services import access


def list_conversations(user: User, workspace_id):
    access.require_permission(user, workspace_id, permissions.KNOWLEDGE_VIEW)
    return (
        AskConversation.objects.filter(workspace_id=workspace_id, user=user)
        .annotate(turn_count=Count("turns"))
        .order_by("-updated_at", "-id")
    )


def get_conversation(user: User, workspace_id, conversation_id) -> AskConversation:
    """The caller's own conversation. Someone else's, or none, is the same 404."""
    access.require_permission(user, workspace_id, permissions.KNOWLEDGE_VIEW)
    try:
        return AskConversation.objects.prefetch_related("turns").get(
            id=conversation_id, workspace_id=workspace_id, user=user
        )
    except AskConversation.DoesNotExist:
        raise NotFoundException(messages.MESSAGE_CONVERSATION_NOT_FOUND) from None


def delete_conversation(user: User, workspace_id, conversation_id) -> None:
    get_conversation(user, workspace_id, conversation_id).delete()


def check_can_add_turn(
    user: User, workspace_id, conversation_id
) -> AskConversation | None:
    """Run before any LLM work: the conversation exists, is the caller's and has room."""
    if conversation_id is None:
        return None
    conversation = get_conversation(user, workspace_id, conversation_id)
    if conversation.turns.count() >= cfg.ASK_MAX_TURNS:
        raise ConflictException(
            messages.MESSAGE_CONVERSATION_FULL.format(limit=cfg.ASK_MAX_TURNS),
            error_code=errors.ERROR_CONVERSATION_FULL,
        )
    return conversation


@transaction.atomic
def record_turn(
    user: User,
    workspace_id,
    conversation: AskConversation | None,
    question: str,
    result: dict,
) -> AskTurn:
    """Store a turn, starting a conversation (titled by its first question) when needed."""
    if conversation is None:
        conversation = AskConversation.objects.create(
            workspace_id=workspace_id,
            user=user,
            title=" ".join(question.split())[: cfg.ASK_TITLE_MAX_LENGTH],
        )
        _prune(user, workspace_id)
    else:
        conversation.save(update_fields=["updated_at"])
    turn = AskTurn.objects.create(
        conversation=conversation, question=question, result=result
    )
    return turn


def _prune(user: User, workspace_id) -> None:
    """Keep the newest ASK_MAX_CONVERSATIONS conversations."""
    keep = list(
        AskConversation.objects.filter(workspace_id=workspace_id, user=user)
        .order_by("-updated_at", "-id")
        .values_list("id", flat=True)[: cfg.ASK_MAX_CONVERSATIONS]
    )
    AskConversation.objects.filter(workspace_id=workspace_id, user=user).exclude(
        id__in=keep
    ).delete()


def delete_for_member(workspace_id, user_id) -> None:
    """A member who leaves or is removed takes their chats with them."""
    AskConversation.objects.filter(workspace_id=workspace_id, user_id=user_id).delete()
