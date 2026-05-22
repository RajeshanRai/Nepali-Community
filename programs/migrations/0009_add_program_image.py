"""Generated migration to add image field to Program model."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0008_alter_program_start_time_alter_program_ticket_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='program_images/', help_text='Primary image used on the program detail and for social sharing'),
        ),
    ]
