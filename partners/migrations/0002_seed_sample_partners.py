from datetime import date

from django.db import migrations


def seed_sample_partners(apps, schema_editor):
    Partner = apps.get_model('partners', 'Partner')

    if Partner.objects.exists():
        return

    Partner.objects.bulk_create([
        Partner(
            name='Nepali Society of British Columbia',
            description='Sample community partner profile representing a cultural society that supports festivals, family gatherings, and newcomer connection across British Columbia.',
            website='https://example.org/nepali-society-bc',
            partnership_since=date(2022, 5, 1),
            social_links={
                'facebook': 'https://example.org/nepali-society-bc/facebook',
                'instagram': 'https://example.org/nepali-society-bc/instagram',
            },
        ),
        Partner(
            name='Nepalese Community Association of Alberta',
            description='Sample partner entry for a prairie-based Nepali association focused on youth engagement, volunteer coordination, and cross-province cultural collaboration.',
            website='https://example.org/nepali-alberta',
            partnership_since=date(2021, 9, 15),
            social_links={
                'facebook': 'https://example.org/nepali-alberta/facebook',
                'linkedin': 'https://example.org/nepali-alberta/linkedin',
            },
        ),
        Partner(
            name='Toronto Nepali Cultural Circle',
            description='Sample cultural partner entry highlighting community performances, heritage workshops, and collaborative events for Nepali families in the Greater Toronto Area.',
            website='https://example.org/toronto-nepali-circle',
            partnership_since=date(2023, 2, 10),
            social_links={
                'facebook': 'https://example.org/toronto-nepali-circle/facebook',
                'twitter': 'https://example.org/toronto-nepali-circle/x',
            },
        ),
        Partner(
            name='Nepali Heritage Network of Canada',
            description='Sample national network profile used to represent partnerships around community storytelling, settlement support, and heritage programming.',
            website='https://example.org/nepali-heritage-canada',
            partnership_since=date(2020, 11, 20),
            social_links={
                'linkedin': 'https://example.org/nepali-heritage-canada/linkedin',
                'instagram': 'https://example.org/nepali-heritage-canada/instagram',
            },
        ),
    ])


def remove_sample_partners(apps, schema_editor):
    Partner = apps.get_model('partners', 'Partner')
    Partner.objects.filter(
        name__in=[
            'Nepali Society of British Columbia',
            'Nepalese Community Association of Alberta',
            'Toronto Nepali Cultural Circle',
            'Nepali Heritage Network of Canada',
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_sample_partners, remove_sample_partners),
    ]