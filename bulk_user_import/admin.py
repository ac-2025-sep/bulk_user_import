from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from import_export.admin import ImportExportModelAdmin

from bulk_user_import.resources import UserResource

@admin.register(User)
class BulkUserImportAdmin(ImportExportModelAdmin, DjangoUserAdmin):
    resource_class = UserResource


User = get_user_model()

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, BulkUserImportAdmin)
