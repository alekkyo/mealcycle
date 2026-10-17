from django.db import migrations


def add_missing_email_addresses(apps, schema_editor):
    """Users created before allauth (e.g. the first superuser) need a verified
    primary EmailAddress to log in by code."""
    User = apps.get_model("accounts", "User")
    EmailAddress = apps.get_model("account", "EmailAddress")
    for user in User.objects.filter(emailaddress__isnull=True):
        EmailAddress.objects.create(
            user=user, email=user.email, verified=True, primary=True
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_backfill_profiles"),
        ("account", "0009_emailaddress_unique_primary_email"),
    ]
    operations = [
        migrations.RunPython(add_missing_email_addresses, migrations.RunPython.noop)
    ]
