from dataclasses import dataclass

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.response.domain import BaseResponseData, SuccessResponse


@dataclass(frozen=True)
class HealthData(BaseResponseData):
    status: str

    def to_dict(self) -> dict:
        return {"status": self.status}


class HealthView(APIView):
    """Liveness probe: no auth, no throttling beyond the anon default."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        return SuccessResponse(data=HealthData(status="ok"), message="OK")
