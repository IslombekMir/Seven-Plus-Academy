from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lessons", "0008_enrollment_is_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="group",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
