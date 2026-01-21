# bulk_user_import

Bulk register/add new users via CSV from Django Admin for Open edX.

## Features
- Adds **Import/Export** actions to the Django Admin User list at `/admin/auth/user/`.
- CSV import supports username, email, first/last name, password (hashed via `set_password`), and staff/superuser flags.
- Idempotent by username (update existing users when username matches).

## Installation

### Install with pip
```bash
pip install bulk-user-import
```

### Enable in Django settings
Add both `import_export` and `bulk_user_import` to `INSTALLED_APPS`:
```python
INSTALLED_APPS += [
    "import_export",
    "bulk_user_import",
]
```

## Tutor/Open edX setup

1. **Add requirements**
   ```bash
   tutor config save --set OPENEDX_EXTRA_PIP_REQUIREMENTS="django-import-export==3.3.7 bulk-user-import"
   ```

2. **Patch `INSTALLED_APPS`** (openedx-common-settings)
   ```yaml
   # tutor/config.yml (patches)
   OPENEDX_COMMON_SETTINGS:
     INSTALLED_APPS:
       - import_export
       - bulk_user_import
   ```

3. **Rebuild and restart**
   ```bash
   tutor dev build lms
   tutor dev restart lms
   # or for local
   tutor local build lms
   tutor local restart lms
   ```

## Admin usage
1. Go to **/admin/auth/user/**.
2. Click **Import**.
3. Upload a CSV file using the format below.

## CSV format
Headers must include `username` and may include the optional fields below.

```csv
username,email,first_name,last_name,password,is_active,is_staff,is_superuser
jdoe,jdoe@example.com,Jane,Doe,MyP@ssw0rd,1,0,0
asmith,asmith@example.com,Alex,Smith,,1,1,0
```

### Notes
- `username` is required.
- `password` is plain text in CSV, but stored hashed via `set_password`.
- If `password` is blank or missing, existing users keep their current password.
- `email`, `first_name`, `last_name` only update when non-blank for existing users.
- Boolean fields accept: `0/1`, `true/false`, `True/False`, `yes/no`.
- Defaults when omitted or blank for new users:
  - `is_active`: `1`
  - `is_staff`: `0`
  - `is_superuser`: `0`

## Running tests
```bash
DJANGO_SETTINGS_MODULE=tests.settings python -m django test
```
