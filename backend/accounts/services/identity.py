from accounts.models import User

GOOGLE_PROVIDER = "google"


def get_google_subject(user: User) -> str | None:
    """The Google `sub` of the user (allauth stores it as SocialAccount.uid)."""
    from allauth.socialaccount.models import SocialAccount

    return (
        SocialAccount.objects.filter(user=user, provider=GOOGLE_PROVIDER)
        .values_list("uid", flat=True)
        .first()
    )
