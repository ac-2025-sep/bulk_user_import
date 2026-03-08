from importlib import import_module


def get_user_profile_model():
    """Return Open edX UserProfile when available, else local fallback model."""

    try:
        module = import_module("common.djangoapps.student.models")
        return module.UserProfile
    except (ImportError, AttributeError):
        from bulk_user_import.models import ImportUserProfile

        return ImportUserProfile
