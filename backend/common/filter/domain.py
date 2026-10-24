from django_filters import rest_framework as filters


class TimeStampFilterMixin(filters.FilterSet):
    """Mix in for any model inheriting TimeStampModel"""

    created_at = filters.DateFromToRangeFilter()
    updated_at = filters.DateFromToRangeFilter()


class SoftDeleteFilterMixin(filters.FilterSet):
    """Mix in for any model inheriting SoftDeleteModel."""

    is_deleted = filters.BooleanFilter()
    deleted_at = filters.DateFromToRangeFilter()
