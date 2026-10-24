from abc import ABC, abstractmethod
from dataclasses import dataclass

from rest_framework.response import Response as DRFResponse

# ── Data shapes (pure data — dataclass is correct here, no HTTP lifecycle) ──


@dataclass(frozen=True)
class BaseResponseData(ABC):
    @abstractmethod
    def to_dict(self) -> dict:
        pass


@dataclass(frozen=True)
class ListResponseData(BaseResponseData):
    items: list[BaseResponseData]

    def to_dict(self) -> dict:
        return {"items": [item.to_dict() for item in self.items]}


# ── Response shapes (these ARE HTTP responses — no dataclass, explicit __init__) ──


class BaseResponse(DRFResponse, ABC):
    default_status_code: int = 200

    default_message: str = ""

    success: bool

    def __init__(
        self, message: str | None = None, status_code: int | None = None, **kwargs
    ):
        self._message = message or self.default_message
        resolved_status = status_code or self.default_status_code

        body = self.build_body(resolved_status)
        super().__init__(data=body, status=resolved_status, **kwargs)

    def build_body(self, status_code: int) -> dict:
        return {
            "success": self.success,
            "status_code": status_code,
            "message": self._message,
        }


class ErrorResponse(BaseResponse):
    success = False

    default_status_code = 500

    def __init__(
        self,
        errors: list[dict] | None = None,
        error_code: str = "internal_error",
        **kwargs,
    ):
        self._errors = errors or []
        self._error_code = error_code
        super().__init__(**kwargs)

    def is_success(self) -> bool:
        return False

    def build_body(self, status_code: int) -> dict:
        body = super().build_body(status_code)
        body["errors"] = self._errors
        body["code"] = self._error_code
        return body


class SuccessResponse(BaseResponse):
    success = True

    default_status_code = 200

    def __init__(
        self, data: BaseResponseData | None = None, meta: dict | None = None, **kwargs
    ):
        self._resource_data = data
        self._meta = meta or {}
        super().__init__(**kwargs)

    def is_success(self) -> bool:
        return True

    def build_body(self, status_code: int) -> dict:
        body = super().build_body(status_code)
        body["data"] = self._resource_data.to_dict() if self._resource_data else None
        body["meta"] = self._meta
        return body


class ResourceCreatedResponse(SuccessResponse):
    default_status_code = 201
    default_message = "Resource created successfully."


class ResourceUpdatedResponse(SuccessResponse):
    default_status_code = 200
    default_message = "Resource updated successfully."


class ResourceDeletedResponse(SuccessResponse):
    default_status_code = 200
    default_message = "Resource deleted successfully."


class ResourceListResponse(SuccessResponse):
    default_status_code = 200
    default_message = "Resources retrieved successfully."
