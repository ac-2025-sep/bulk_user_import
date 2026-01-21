import tablib
from django.contrib.auth import get_user_model
from django.test import TestCase

from bulk_user_import.resources import UserResource


class UserImportTests(TestCase):
    def setUp(self):
        self.resource = UserResource()
        self.user_model = get_user_model()

    def test_import_creates_user_with_hashed_password(self):
        dataset = tablib.Dataset(
            [
                "importuser",
                "import@example.com",
                "Import",
                "User",
                "secretpass",
                "1",
                "0",
                "0",
            ],
            headers=[
                "username",
                "email",
                "first_name",
                "last_name",
                "password",
                "is_active",
                "is_staff",
                "is_superuser",
            ],
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        user = self.user_model.objects.get(username="importuser")
        self.assertTrue(user.check_password("secretpass"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_reimport_updates_fields_without_changing_password(self):
        user = self.user_model.objects.create_user(
            username="existing",
            email="original@example.com",
            password="originalpass",
        )

        dataset = tablib.Dataset(
            [
                "existing",
                "",
                "Updated",
                "Name",
                "",
                "",
                "yes",
                "",
            ],
            headers=[
                "username",
                "email",
                "first_name",
                "last_name",
                "password",
                "is_active",
                "is_staff",
                "is_superuser",
            ],
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        user.refresh_from_db()
        self.assertEqual(user.email, "original@example.com")
        self.assertEqual(user.first_name, "Updated")
        self.assertEqual(user.last_name, "Name")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password("originalpass"))

    def test_import_handles_duplicate_usernames(self):
        dataset = tablib.Dataset(
            [
                "dupe",
                "first@example.com",
                "First",
                "User",
                "pass1",
                "1",
                "0",
                "0",
            ],
            [
                "dupe",
                "second@example.com",
                "Second",
                "User",
                "pass2",
                "1",
                "1",
                "0",
            ],
            headers=[
                "username",
                "email",
                "first_name",
                "last_name",
                "password",
                "is_active",
                "is_staff",
                "is_superuser",
            ],
        )

        result = self.resource.import_data(dataset, dry_run=False)

        self.assertFalse(result.has_errors())
        self.assertEqual(self.user_model.objects.filter(username="dupe").count(), 1)
        user = self.user_model.objects.get(username="dupe")
        self.assertEqual(user.email, "second@example.com")
        self.assertEqual(user.first_name, "Second")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password("pass2"))
