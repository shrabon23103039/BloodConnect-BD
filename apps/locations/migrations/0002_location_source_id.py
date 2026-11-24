from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("locations", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="location",
            name="source_id",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddConstraint(
            model_name="location",
            constraint=models.UniqueConstraint(
                condition=Q(source_id__isnull=False),
                fields=("source_name", "source_id"),
                name="locations_source_id_uniq",
            ),
        ),
    ]
