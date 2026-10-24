from dataclasses import dataclass

from allauth.usersessions.models import UserSession

from accounts.models import User
from accounts.services.device import device_label
from common.response.domain import BaseResponseData


@dataclass(frozen=True)
class ProfileData(BaseResponseData):
    user: User

    def to_dict(self) -> dict:
        user = self.user
        return {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat(),
        }


@dataclass(frozen=True)
class SessionData(BaseResponseData):
    session: UserSession
    is_current: bool

    def to_dict(self) -> dict:
        s = self.session  # the IP address is stored but never returned
        return {
            "id": s.pk,
            "device": device_label(s.user_agent),
            "created_at": s.created_at.isoformat(),
            "last_active_at": s.last_seen_at.isoformat(),
            "is_current": self.is_current,
        }


@dataclass(frozen=True)
class MessageData(BaseResponseData):
    detail: str = ""

    def to_dict(self) -> dict:
        return {"detail": self.detail}
