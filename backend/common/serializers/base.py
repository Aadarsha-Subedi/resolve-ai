from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    """Rejects request bodies that carry fields the serializer does not declare."""

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {name: "Unknown field." for name in sorted(unknown)}
                )
        return super().to_internal_value(data)

    @classmethod
    def parse(cls, data) -> dict:
        """Validate a request body and return the cleaned data, or raise."""
        serializer = cls(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data
