from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Profile = apps.get_model("accounts", "Profile")
    for user in User.objects.filter(profile__isnull=True):
        Profile.objects.create(user=user, trial_started_at=user.date_joined)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_profile")]
    operations = [
        migrations.RunPython(create_missing_profiles, migrations.RunPython.noop)
    ]
