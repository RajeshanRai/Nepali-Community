from datetime import date

from django.db import migrations


PARTNERS = [
    {
        'name': 'Vancouver Nepali Cultural Society',
        'description': 'Sample Vancouver-based partner profile focused on cultural showcases, intergenerational learning, and local community celebrations.',
        'website': 'https://example.org/vancouver-nepali-cultural-society',
        'partnership_since': date(2023, 4, 6),
        'social_links': {
            'facebook': 'https://example.org/vancouver-nepali-cultural-society/facebook',
            'instagram': 'https://example.org/vancouver-nepali-cultural-society/instagram',
        },
    },
    {
        'name': 'Surrey Nepali Family Network',
        'description': 'Sample Surrey-area partner entry representing family support programs, youth outreach, and neighborhood volunteer coordination.',
        'website': 'https://example.org/surrey-nepali-family-network',
        'partnership_since': date(2022, 8, 14),
        'social_links': {
            'facebook': 'https://example.org/surrey-nepali-family-network/facebook',
            'linkedin': 'https://example.org/surrey-nepali-family-network/linkedin',
        },
    },
    {
        'name': 'Burnaby Nepali Community Circle',
        'description': 'Sample Burnaby partner listing for local meetups, wellness support, and collaborative cultural programming across the Lower Mainland.',
        'website': 'https://example.org/burnaby-nepali-community-circle',
        'partnership_since': date(2024, 1, 18),
        'social_links': {
            'facebook': 'https://example.org/burnaby-nepali-community-circle/facebook',
            'instagram': 'https://example.org/burnaby-nepali-community-circle/instagram',
        },
    },
    {
        'name': 'Lower Mainland Nepali Youth Collective',
        'description': 'Sample regional youth-focused partner supporting leadership events, volunteering, and cultural storytelling across Metro Vancouver.',
        'website': 'https://example.org/lower-mainland-nepali-youth-collective',
        'partnership_since': date(2021, 6, 3),
        'social_links': {
            'instagram': 'https://example.org/lower-mainland-nepali-youth-collective/instagram',
            'linkedin': 'https://example.org/lower-mainland-nepali-youth-collective/linkedin',
        },
    },
]


def seed_lower_mainland_partners(apps, schema_editor):
    Partner = apps.get_model('partners', 'Partner')

    existing_names = set(Partner.objects.values_list('name', flat=True))
    to_create = [Partner(**partner) for partner in PARTNERS if partner['name'] not in existing_names]

    if to_create:
        Partner.objects.bulk_create(to_create)


def remove_lower_mainland_partners(apps, schema_editor):
    Partner = apps.get_model('partners', 'Partner')
    Partner.objects.filter(name__in=[partner['name'] for partner in PARTNERS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0002_seed_sample_partners'),
    ]

    operations = [
        migrations.RunPython(seed_lower_mainland_partners, remove_lower_mainland_partners),
    ]