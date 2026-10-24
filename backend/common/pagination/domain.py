from abc import ABC, abstractmethod

from rest_framework.pagination import CursorPagination, LimitOffsetPagination


class BasePagination(ABC):
    """Contract every pagination style must satisfy - regardless of whether it is offset based or cursor-based under the hood."""

    @abstractmethod
    def get_meta(self) -> dict:
        """Returns the pagination info that goes into SuccessResponse.meta —
        e.g. {"count": ..., "next": ..., "previous": ...}."""
        ...


class OffsetBasedPagination(LimitOffsetPagination, BasePagination):
    default_limit = 25

    max_limit = 100

    def get_meta(self) -> dict:

        return {
            "count": self.count,
            "limit": self.limit,
            "offset": self.offset,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
        }


class CursorBasedPagination(CursorPagination, BasePagination):
    page_size = 20

    ordering = "-created_at"

    def get_meta(self) -> dict:

        return {"next": self.get_next_link(), "previous": self.get_previous_link()}
