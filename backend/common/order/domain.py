from common.order.constants import (
    SOFT_DELETE_ORDERING_FIELDS,
    TIMESTAMP_ORDERING_FIELDS,
)


class TimeStampOrderingMixin:
    ordering_fields = TIMESTAMP_ORDERING_FIELDS


class SoftDeleteOrderingMixin:
    ordering_fields = SOFT_DELETE_ORDERING_FIELDS


class OrderingFieldsMixin:
    """Single mixin — configure via flags instead of stacking a
    mixin per trait."""

    extra_ordering_fields: list[str] = []

    include_timestamp_order: bool = True

    # Opt-in since not every model has it
    include_soft_delete_ordering: bool = False

    @property
    def ordering_fields(self) -> list[str]:

        fields: list[str] = []

        if self.include_timestamp_order:
            fields += TIMESTAMP_ORDERING_FIELDS

        if self.include_soft_delete_ordering:
            fields += SOFT_DELETE_ORDERING_FIELDS

        fields += self.extra_ordering_fields

        return list(dict.fromkeys(fields))
