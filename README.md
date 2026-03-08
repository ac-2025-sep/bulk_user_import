# bulk_user_import

Bulk import users via CSV from Django Admin using `django-import-export`.

## Scope and compatibility

This package is designed for Open edX deployments and integrates with `common.djangoapps.student.models.UserProfile` when available.

For non-Open-edX test/dev environments, it falls back to an internal profile model so imports still run, but production metadata behavior is intended for Open edX.

## Features

- Admin import/export integration on `/admin/auth/user/`
- Upsert by `username` (`import_id_fields = ("username",)`)
- Password handling with `set_password()` (never stores plaintext)
- Flexible boolean parsing for `is_active`, `is_staff`, `is_superuser`
- Metadata columns imported into `UserProfile.meta` JSON under `meta["org"]`

## Installation

```bash
pip install bulk-user-import
```

Add apps:

```python
INSTALLED_APPS += [
    "import_export",
    "bulk_user_import",
]
```

## CSV format

### Core columns

`username` is required. Other columns are optional.

```csv
username,email,first_name,last_name,password,is_active,is_staff,is_superuser
jdoe,jdoe@example.com,Jane,Doe,MyP@ssw0rd,1,0,0
asmith,asmith@example.com,Alex,Smith,,1,1,0
```

### Metadata columns

The following optional CSV headers map into `UserProfile.meta["org"]`:

- `DEALER ID` -> `dealer_id`
- `CHAMPION NAME` -> `champion_name`
- `CHAMPION MOB.` -> `champion_mobile`
- `DEALER NAME` -> `dealer_name`
- `CITY` -> `city`
- `STATE` -> `state`
- `DEALER CATEGORY` -> `dealer_category`
- `CLUSTER` -> `cluster`
- `ASM` -> `asm`
- `RSM` -> `rsm`
- `ROLE` -> `role`
- `DEPARTMENT` -> `department`
- `BRAND` -> `brand`

## Import behavior

- `username` is required and used to identify existing rows.
- Existing users are updated; new users are created.
- `email`, `first_name`, `last_name`:
  - for existing users, blank CSV values do **not** overwrite existing values.
- Password:
  - non-blank CSV password is hashed via `set_password()`.
  - blank/missing password does not change existing password.
  - new users with blank password keep Django's default unusable/empty-password behavior.
- Booleans accept: `1/0`, `true/false`, `yes/no`, `y/n`, `t/f` (case-insensitive).
  - blank/missing booleans default to `is_active=True`, `is_staff=False`, `is_superuser=False` for new users.
- Metadata merge:
  - existing `meta` JSON is parsed safely.
  - malformed/non-dict existing meta falls back to `{}`.
  - unrelated keys in `meta` are preserved.
  - blank metadata CSV values are ignored (do not clear existing keys).

## Running tests

```bash
DJANGO_SETTINGS_MODULE=tests.settings python -m django test
```
