# Generated by Django 5.0.3 on 2024-04-11 16:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("walkinter", "0002_photo"),
    ]

    operations = [
        migrations.CreateModel(
            name="GPSData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
