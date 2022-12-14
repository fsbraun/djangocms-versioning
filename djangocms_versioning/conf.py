from django.conf import settings


ENABLE_MENU_REGISTRATION = getattr(
    settings, "DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION", True
)

EXTENDED_MENU = getattr(
    settings, "DJANGOCMS_VERSIONING_EXTENDED_MENU", 7
)
