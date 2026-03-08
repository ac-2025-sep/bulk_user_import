from django.conf import settings
from django.db import models


class ImportUserProfile(models.Model):
    """Fallback profile model used when Open edX UserProfile is unavailable."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    meta = models.TextField(blank=True, default="")

    class Meta:
        app_label = "bulk_user_import"
        verbose_name = "Import User Profile"
        verbose_name_plural = "Import User Profiles"
