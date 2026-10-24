from rest_framework.request import Request

from common.pagination.domain import OffsetBasedPagination


def paginate(request: Request, queryset):
    """Returns (page items, meta) using the shared offset pagination (25, max 100)."""
    paginator = OffsetBasedPagination()
    page = paginator.paginate_queryset(queryset, request)
    return page, paginator.get_meta()
