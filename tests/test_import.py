import json

import tablib
from django.contrib.auth import get_user_model
from django.test import TestCase

from bulk_user_import.profiles import get_user_profile_model
from bulk_user_import.resources import UserResource


BASE_HEADERS = [
    "username",
    "email",
    "first_name",
    "last_name",
    "password",
    "is_active",
    "is_staff",
    "is_superuser",
    "DEALER ID",
    "CHAMPION NAME",
    "CHAMPION MOB.",
    "DEALER NAME",
    "CITY",
    "STATE",
    "DEALER CATEGORY",
    "CLUSTER",
    "ASM",
    "RSM",
    "ROLE",
    "DEPARTMENT",
    "BRAND",
]


def build_dataset(*rows):
    return tablib.Dataset(*rows, headers=BASE_HEADERS)


class UserImportTests(TestCase):
    def setUp(self):
        self.resource = UserResource()
        self.user_model = get_user_model()
        self.profile_model = get_user_profile_model()

    def _org_meta(self, username):
        user = self.user_model.objects.get(username=username)
        profile = self.profile_model.objects.get(user=user)
        return json.loads(profile.meta).get("org", {})

    def test_create_new_user(self):
        dataset = build_dataset(
            ["newuser", "new@example.com", "New", "User", "", "1", "0", "0", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        user = self.user_model.objects.get(username="newuser")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")

    def test_update_existing_user_by_username(self):
        self.user_model.objects.create_user(username="existing", email="old@example.com", first_name="Old")
        dataset = build_dataset(
            ["existing", "updated@example.com", "Updated", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        user = self.user_model.objects.get(username="existing")
        self.assertEqual(user.email, "updated@example.com")
        self.assertEqual(user.first_name, "Updated")

    def test_password_set_on_create(self):
        dataset = build_dataset(
            ["pwduser", "pwd@example.com", "Pwd", "User", "secretpass", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        user = self.user_model.objects.get(username="pwduser")
        self.assertTrue(user.check_password("secretpass"))

    def test_password_unchanged_when_blank(self):
        user = self.user_model.objects.create_user(username="existing", email="e@example.com", password="oldpass")
        dataset = build_dataset(
            ["existing", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        user.refresh_from_db()
        self.assertTrue(user.check_password("oldpass"))

    def test_boolean_parsing(self):
        dataset = build_dataset(
            ["bool1", "", "", "", "", "yes", "1", "false", "", "", "", "", "", "", "", "", "", "", "", "", ""],
            ["bool2", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        user1 = self.user_model.objects.get(username="bool1")
        user2 = self.user_model.objects.get(username="bool2")
        self.assertTrue(user1.is_active)
        self.assertTrue(user1.is_staff)
        self.assertFalse(user1.is_superuser)
        self.assertTrue(user2.is_active)
        self.assertFalse(user2.is_staff)
        self.assertFalse(user2.is_superuser)

    def test_metadata_written_to_profile_meta(self):
        dataset = build_dataset(
            [
                "metauser",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "D001",
                "Jane Champion",
                "99999",
                "Dealer One",
                "Bengaluru",
                "KA",
                "Gold",
                "C1",
                "Asm Name",
                "Rsm Name",
                "Manager",
                "Sales",
                "BrandX",
            ]
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        org = self._org_meta("metauser")
        self.assertEqual(org["dealer_id"], "D001")
        self.assertEqual(org["champion_mobile"], "99999")

    def test_existing_metadata_preserved(self):
        user = self.user_model.objects.create_user(username="meta", email="m@example.com")
        self.profile_model.objects.create(user=user, meta=json.dumps({"foo": "bar", "org": {"city": "Old"}}))

        dataset = build_dataset(
            ["meta", "", "", "", "", "", "", "", "", "", "", "", "New City", "", "", "", "", "", "", "", ""]
        )
        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        profile = self.profile_model.objects.get(user=user)
        meta = json.loads(profile.meta)
        self.assertEqual(meta["foo"], "bar")
        self.assertEqual(meta["org"]["city"], "New City")

    def test_malformed_existing_meta_handled(self):
        user = self.user_model.objects.create_user(username="badmeta")
        self.profile_model.objects.create(user=user, meta="not-json")
        dataset = build_dataset(
            ["badmeta", "", "", "", "", "", "", "", "", "", "", "", "", "TN", "", "", "", "", "", "", ""]
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        org = self._org_meta("badmeta")
        self.assertEqual(org["state"], "TN")

    def test_missing_profile_is_created(self):
        self.user_model.objects.create_user(username="noprofile")
        dataset = build_dataset(
            ["noprofile", "", "", "", "", "", "", "", "", "", "", "", "", "MH", "", "", "", "", "", "", ""]
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        self.assertTrue(self.profile_model.objects.filter(user__username="noprofile").exists())

    def test_import_is_idempotent_by_username(self):
        dataset = build_dataset(
            ["dupe", "first@example.com", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
            ["dupe", "second@example.com", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        self.assertEqual(self.user_model.objects.filter(username="dupe").count(), 1)
        self.assertEqual(self.user_model.objects.get(username="dupe").email, "second@example.com")

    def test_blank_non_required_fields_do_not_overwrite_existing(self):
        self.user_model.objects.create_user(
            username="keep",
            email="keep@example.com",
            first_name="Keep",
            last_name="Me",
        )
        dataset = build_dataset(
            ["keep", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        user = self.user_model.objects.get(username="keep")
        self.assertEqual(user.email, "keep@example.com")
        self.assertEqual(user.first_name, "Keep")
        self.assertEqual(user.last_name, "Me")
