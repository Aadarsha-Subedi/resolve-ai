from django.db import IntegrityError, transaction
from django.template.defaultfilters import slugify

from accounts.models import User
from common.exception.domain import ConflictException, NotFoundException
from knowledge.constants import errors, messages
from knowledge.constants.settings import CATEGORY_SLUG_MAX_LENGTH, DEFAULT_CATEGORIES
from knowledge.models import KnowledgeCategory
from knowledge.services import hooks
from workspaces.constants import permissions
from workspaces.services import access


def _slug(name: str) -> str:
    return slugify(name)[:CATEGORY_SLUG_MAX_LENGTH] or "category"


def seed_defaults(workspace_id) -> None:
    """Create the default categories (idempotent)."""
    for name in DEFAULT_CATEGORIES:
        KnowledgeCategory.objects.get_or_create(
            workspace_id=workspace_id, slug=_slug(name), defaults={"name": name}
        )


def list_categories(user: User, workspace_id):
    access.require_permission(user, workspace_id, permissions.KNOWLEDGE_VIEW)
    return KnowledgeCategory.objects.filter(workspace_id=workspace_id)


def create_category(user: User, workspace_id, name: str) -> KnowledgeCategory:
    membership = access.require_permission(
        user, workspace_id, permissions.KNOWLEDGE_MANAGE
    )
    try:
        with transaction.atomic():
            category = KnowledgeCategory.objects.create(
                workspace_id=workspace_id, name=name, slug=_slug(name)
            )
    except IntegrityError:
        raise _exists() from None
    hooks.emit(membership.workspace, user, hooks.ACTION_CATEGORY_CREATED)
    return category


def get_category(workspace_id, category_id) -> KnowledgeCategory:
    category = KnowledgeCategory.objects.filter(
        workspace_id=workspace_id, pk=category_id
    ).first()
    if category is None:
        raise NotFoundException(messages.MESSAGE_CATEGORY_NOT_FOUND)
    return category


def rename_category(
    user: User, workspace_id, category_id, name: str
) -> KnowledgeCategory:
    membership = access.require_permission(
        user, workspace_id, permissions.KNOWLEDGE_MANAGE
    )
    category = get_category(workspace_id, category_id)
    category.name = name
    category.slug = _slug(name)
    try:
        with transaction.atomic():
            category.save(update_fields=["name", "slug", "updated_at"])
    except IntegrityError:
        raise _exists() from None
    hooks.emit(membership.workspace, user, hooks.ACTION_CATEGORY_UPDATED)
    return category


def delete_category(user: User, workspace_id, category_id) -> None:
    """Deleting a category only unlinks it from articles; the articles stay."""
    membership = access.require_permission(
        user, workspace_id, permissions.KNOWLEDGE_MANAGE
    )
    get_category(workspace_id, category_id).delete()
    hooks.emit(membership.workspace, user, hooks.ACTION_CATEGORY_DELETED)


def _exists() -> ConflictException:
    return ConflictException(
        messages.MESSAGE_CATEGORY_EXISTS, error_code=errors.ERROR_CATEGORY_EXISTS
    )
