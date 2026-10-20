from rest_framework.throttling import (
    AnonRateThrottle,
    ScopedRateThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)


class AnonThrottle(AnonRateThrottle):
    """60/min per IP for anonymous callers (rate set in REST_FRAMEWORK)."""

    scope = "anon"


class UserThrottle(UserRateThrottle):
    """600/min per signed-in user (rate set in REST_FRAMEWORK)."""

    scope = "user"


class AuthScopedThrottle(ScopedRateThrottle):
    """Per-view named limits (login, signup, password_reset, ...). A view opts
    in by setting `throttle_scope`. Keyed by IP for anonymous callers."""


class WorkspaceThrottle(SimpleRateThrottle):
    """Caps all traffic to one workspace (every member together) so a single busy
    workspace cannot starve the others. Applies only to routes that carry a
    `workspace_id` URL kwarg; everything else is ignored."""

    scope = "workspace"

    def get_cache_key(self, request, view) -> str | None:
        workspace_id = getattr(view, "kwargs", {}).get("workspace_id")
        if workspace_id is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(workspace_id)}
