from django.conf import settings


ENABLE_MENU_REGISTRATION = getattr(
    settings, "DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION", True
)

STRICT_VERSIONING = getattr(
    settings, "DJANGOCMS_VERSIONING_STRICT", True
)

USERNAME_FIELD = getattr(
    settings, "DJANGOCMS_VERSIONING_USERNAME_FIELD", 'username'
)

DEFAULT_USER = getattr(
    settings, "DJANGOCMS_VERSIONING_DEFAULT_USER", None
)
