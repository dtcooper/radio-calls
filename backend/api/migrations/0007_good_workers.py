# Generated by Django 5.0.4 on 2024-04-10 18:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0006_assignment_user_agent"),
    ]

    operations = [
        migrations.AddField(
            model_name="worker",
            name="is_good_worker",
            field=models.BooleanField(
                default=False,
                help_text='Mark worker as "good", and ignore any accidental block attempts.',
                verbose_name="good worker",
            ),
        ),
        migrations.AlterField(
            model_name="hit",
            name="qualification_adult",
            field=models.BooleanField(
                default=False,
                help_text="Worker qualification. Enable to require workers to be over 18.",
                verbose_name="adult qualification",
            ),
        ),
        migrations.AlterField(
            model_name="workerpageload",
            name="assignment_amazon_id",
            field=models.CharField(
                blank=True,
                help_text="Assignment identifier as used by the Amazon MTurk API.",
                max_length=255,
                null=True,
                verbose_name="assignment Amazon ID",
            ),
        ),
        migrations.AlterField(
            model_name="workerpageload",
            name="had_amp_encoded",
            field=models.BooleanField(
                default=False,
                help_text="Request had &amp; encoded. This appears to be a marker of spam.",
                verbose_name="had &amp; encoded",
            ),
        ),
        migrations.AlterField(
            model_name="workerpageload",
            name="worker_amazon_id",
            field=models.CharField(
                db_index=True,
                help_text="Worker identifier as used by the Amazon MTurk API.",
                max_length=255,
                verbose_name="worker Amazon ID",
            ),
        ),
    ]
