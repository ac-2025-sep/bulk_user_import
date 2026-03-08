import json

from django.contrib.auth import get_user_model
from import_export import fields, resources
from import_export.widgets import BooleanWidget

from bulk_user_import.profiles import get_user_profile_model


class FlexibleBooleanWidget(BooleanWidget):
    TRUE_VALUES = ("1", "true", "yes", "y", "t")
    FALSE_VALUES = ("0", "false", "no", "n", "f")

    def clean(self, value, row=None, *args, **kwargs):
        parsed = parse_boolean(value)
        if parsed is None:
            return None
        return parsed


def parse_boolean(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value

    text = str(value).strip()
    if not text:
        return None

    lowered = text.lower()
    if lowered in FlexibleBooleanWidget.TRUE_VALUES:
        return True
    if lowered in FlexibleBooleanWidget.FALSE_VALUES:
        return False
    return None


class UserResource(resources.ModelResource):
    """Import users for Open edX admin CSV workflows."""

    META_FIELD_MAP = (
        ("DEALER ID", "dealer_id"),
        ("CHAMPION NAME", "champion_name"),
        ("CHAMPION MOB.", "champion_mobile"),
        ("DEALER NAME", "dealer_name"),
        ("CITY", "city"),
        ("STATE", "state"),
        ("DEALER CATEGORY", "dealer_category"),
        ("CLUSTER", "cluster"),
        ("ASM", "asm"),
        ("RSM", "rsm"),
        ("ROLE", "role"),
        ("DEPARTMENT", "department"),
        ("BRAND", "brand"),
    )

    password = fields.Field(column_name="password", readonly=True)

    is_active = fields.Field(column_name="is_active", attribute="is_active", widget=FlexibleBooleanWidget())
    is_staff = fields.Field(column_name="is_staff", attribute="is_staff", widget=FlexibleBooleanWidget())
    is_superuser = fields.Field(column_name="is_superuser", attribute="is_superuser", widget=FlexibleBooleanWidget())

    dealer_id = fields.Field(column_name="DEALER ID", readonly=True)
    champion_name = fields.Field(column_name="CHAMPION NAME", readonly=True)
    champion_mob = fields.Field(column_name="CHAMPION MOB.", readonly=True)
    dealer_name = fields.Field(column_name="DEALER NAME", readonly=True)
    city = fields.Field(column_name="CITY", readonly=True)
    state = fields.Field(column_name="STATE", readonly=True)
    dealer_category = fields.Field(column_name="DEALER CATEGORY", readonly=True)
    cluster = fields.Field(column_name="CLUSTER", readonly=True)
    asm = fields.Field(column_name="ASM", readonly=True)
    rsm = fields.Field(column_name="RSM", readonly=True)
    role = fields.Field(column_name="ROLE", readonly=True)
    department = fields.Field(column_name="DEPARTMENT", readonly=True)
    brand = fields.Field(column_name="BRAND", readonly=True)

    class Meta:
        model = get_user_model()
        import_id_fields = ("username",)
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "is_active",
            "is_staff",
            "is_superuser",
            "dealer_id",
            "champion_name",
            "champion_mob",
            "dealer_name",
            "city",
            "state",
            "dealer_category",
            "cluster",
            "asm",
            "rsm",
            "role",
            "department",
            "brand",
        )

    def before_import_row(self, row, **kwargs):
        for key, value in list(row.items()):
            if isinstance(value, str):
                row[key] = value.strip()

        username = self._get_row_value(row, "username")
        if not username:
            raise ValueError("username is required")

        return super().before_import_row(row, **kwargs)

    def import_obj(self, obj, data, dry_run, **kwargs):
        self._apply_row_overrides(obj, data)
        obj._import_password = self._clean_password(data)
        obj._import_metadata = self._collect_metadata(data)
        return super().import_obj(obj, data, dry_run, **kwargs)

    def before_save_instance(self, instance, row, **kwargs):
        password = getattr(instance, "_import_password", None)
        if password:
            instance.set_password(password)
        return super().before_save_instance(instance, row, **kwargs)

    def after_save_instance(self, instance, row, **kwargs):
        super().after_save_instance(instance, row, **kwargs)
        if kwargs.get("dry_run"):
            return

        self._persist_profile_metadata(instance, getattr(instance, "_import_metadata", {}))

        if hasattr(instance, "_import_password"):
            delattr(instance, "_import_password")
        if hasattr(instance, "_import_metadata"):
            delattr(instance, "_import_metadata")

    def _apply_row_overrides(self, user, row):
        for field in ("email", "first_name", "last_name"):
            if not self._row_has_key(row, field):
                continue
            if user.pk and self._is_blank(self._get_row_value(row, field)):
                row[field] = getattr(user, field)

        defaults = {"is_active": True, "is_staff": False, "is_superuser": False}
        for field in defaults:
            if not self._row_has_key(row, field):
                continue

            parsed = parse_boolean(self._get_row_value(row, field))
            if parsed is None:
                row[field] = getattr(user, field) if user.pk else defaults[field]
            else:
                row[field] = parsed

    def _collect_metadata(self, row):
        collected = {}
        for column_name, meta_key in self.META_FIELD_MAP:
            value = self._get_row_value(row, column_name)
            if self._is_blank(value):
                continue
            collected[meta_key] = value.strip() if isinstance(value, str) else value
        return collected

    def _persist_profile_metadata(self, user, imported_meta):
        profile_model = get_user_profile_model()
        profile, _ = profile_model.objects.get_or_create(user=user)

        existing_meta = self._parse_meta(profile.meta)
        org_meta = existing_meta.get("org")
        if not isinstance(org_meta, dict):
            org_meta = {}

        org_meta.update(imported_meta)
        existing_meta["org"] = org_meta

        profile.meta = json.dumps(existing_meta, ensure_ascii=False)
        profile.save(update_fields=["meta"])

    @staticmethod
    def _clean_password(row):
        value = UserResource._get_row_value(row, "password")
        if isinstance(value, str):
            value = value.strip()
        return value or None

    @staticmethod
    def _parse_meta(value):
        if not value:
            return {}
        if isinstance(value, dict):
            return value

        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _is_blank(value):
        return value is None or (isinstance(value, str) and value.strip() == "")

    @staticmethod
    def _get_row_value(row, key):
        if hasattr(row, "get"):
            return row.get(key)
        try:
            return row[key]
        except (KeyError, TypeError):
            return None

    @staticmethod
    def _row_has_key(row, key):
        try:
            return key in row
        except TypeError:
            try:
                row[key]
                return True
            except KeyError:
                return False
