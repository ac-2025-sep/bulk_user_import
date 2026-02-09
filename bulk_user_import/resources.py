from django.contrib.auth import get_user_model
from import_export import fields, resources
from import_export.widgets import BooleanWidget
from common.djangoapps.student.models import UserProfile
import json



class FlexibleBooleanWidget(BooleanWidget):
    TRUE_VALUES = ("1", "true", "yes", "y", "t")
    FALSE_VALUES = ("0", "false", "no", "n", "f")

    def clean(self, value, row=None, *args, **kwargs):
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        text = str(value).strip()
        if text == "":
            return None
        lowered = text.lower()
        if lowered in self.TRUE_VALUES:
            return True
        if lowered in self.FALSE_VALUES:
            return False
        return super().clean(text, row=row, *args, **kwargs)


class UserResource(resources.ModelResource):
    password = fields.Field(column_name="password")
    is_active = fields.Field(column_name="is_active", attribute="is_active", widget=FlexibleBooleanWidget())
    is_staff = fields.Field(column_name="is_staff", attribute="is_staff", widget=FlexibleBooleanWidget())
    is_superuser = fields.Field(
        column_name="is_superuser",
        attribute="is_superuser",
        widget=FlexibleBooleanWidget(),
    )

    dealer_id = fields.Field(column_name="DEALER ID")
    champion_name = fields.Field(column_name="CHAMPION NAME")
    champion_mob = fields.Field(column_name="CHAMPION MOB.")
    dealer_name = fields.Field(column_name="DEALER NAME")
    city = fields.Field(column_name="CITY")
    state = fields.Field(column_name="STATE")
    dealer_category = fields.Field(column_name="DEALER CATEGORY")
    cluster = fields.Field(column_name="CLUSTER")
    asm_1 = fields.Field(column_name="ASM 1")
    asm_2 = fields.Field(column_name="ASM 2")


    fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "password",
        "is_active",
        "is_staff",
        "is_superuser",

        # NEW columns from CSV
        "dealer_id",
        "champion_name",
        "champion_mob",
        "dealer_name",
        "city",
        "state",
        "dealer_category",
        "cluster",
        "asm_1",
        "asm_2",
    )

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
    
            # 👇 ADD THESE
            "dealer_id",
            "champion_name",
            "champion_mob",
            "dealer_name",
            "city",
            "state",
            "dealer_category",
            "cluster",
            "asm_1",
            "asm_2",
        )

    # class Meta:
    #     model = get_user_model()
    #     import_id_fields = ("username",)
    #     fields = (
    #         "username",
    #         "email",
    #         "first_name",
    #         "last_name",
    #         "password",
    #         "is_active",
    #         "is_staff",
    #         "is_superuser",
    #     )

    def before_import_row(self, row, **kwargs):
        for field in ("username", "email"):
            if self._row_has_key(row, field):
                value = self._get_row_value(row, field)
                if isinstance(value, str):
                    row[field] = value.strip()
        return super().before_import_row(row, **kwargs)

    # def import_obj(self, obj, data, dry_run):
    #     self._apply_row_overrides(obj, data)
    #     super().import_obj(obj, data, dry_run)
    #     password = self._get_row_value(data, "password") if self._row_has_key(data, "password") else None
    #     if isinstance(password, str):
    #         password = password.strip()
    #     if password:
    #         obj.set_password(password)

    def import_obj(self, obj, data, dry_run, **kwargs):
        # Apply your existing overrides
        self._apply_row_overrides(obj, data)

        # Let import-export populate User fields
        super().import_obj(obj, data, dry_run)

        # Password handling (unchanged)
        password = self._get_row_value(data, "password") if self._row_has_key(data, "password") else None
        if isinstance(password, str):
            password = password.strip()
        if password:
            obj.set_password(password)

    def after_save_instance(self, instance, row, **kwargs):
        super().after_save_instance(instance, row, **kwargs)
        if self._is_dry_run(kwargs):
            return
        self._update_profile_meta(instance, row)

    def _update_profile_meta(self, obj, data):
        profile, _ = UserProfile.objects.get_or_create(user=obj)

        meta_raw = profile.meta
        if not meta_raw:
            meta = {}
        elif isinstance(meta_raw, dict):
            meta = meta_raw
        else:
            try:
                meta = json.loads(meta_raw)
                if not isinstance(meta, dict):
                    meta = {}
            except Exception:
                meta = {}

        org = meta.get("org", {})

        def val(col):
            v = self._get_row_value(data, col)
            return v.strip() if isinstance(v, str) else v

        org.update({
            "dealer_id": val("DEALER ID"),
            "champion_name": val("CHAMPION NAME"),
            "champion_mobile": val("CHAMPION MOB."),
            "dealer_name": val("DEALER NAME"),
            "city": val("CITY"),
            "state": val("STATE"),
            "dealer_category": val("DEALER CATEGORY"),
            "cluster": val("CLUSTER"),
            "asm_1": val("ASM 1"),
            "asm_2": val("ASM 2"),
        })

        meta["org"] = org
        profile.meta = json.dumps(meta, ensure_ascii=False)
        profile.save()


    def _apply_row_overrides(self, obj, row):
        for field in ("email", "first_name", "last_name"):
            if not self._row_has_key(row, field):
                continue
            value = self._get_row_value(row, field)
            if obj.pk and self._is_blank(value):
                row[field] = getattr(obj, field)

        defaults = {
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        }
        for field in ("is_active", "is_staff", "is_superuser"):
            if not self._row_has_key(row, field):
                continue
            value = self._get_row_value(row, field)
            parsed = self._parse_boolean(value)
            if parsed is None:
                row[field] = getattr(obj, field) if obj.pk else defaults[field]
            else:
                row[field] = parsed

    @staticmethod
    def _is_blank(value):
        return value is None or (isinstance(value, str) and value.strip() == "")

    @staticmethod
    def _parse_boolean(value):
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        text = str(value).strip()
        if text == "":
            return None
        lowered = text.lower()
        if lowered in FlexibleBooleanWidget.TRUE_VALUES:
            return True
        if lowered in FlexibleBooleanWidget.FALSE_VALUES:
            return False
        return None

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
                
