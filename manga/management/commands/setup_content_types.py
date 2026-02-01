from django.core.management.base import BaseCommand
from manga.models import ContentType

class Command(BaseCommand):
    help = 'Setup default content types'
    
    def handle(self, *args, **options):
        content_types = [
            {
                'name': 'Manga',
                'default_orientation': 'horizontal',
                'description': 'Japanese comics, read right to left'
            },
            {
                'name': 'Manhwa',
                'default_orientation': 'vertical',
                'description': 'Korean comics, vertical scroll'
            },
            {
                'name': 'Manhua',
                'default_orientation': 'vertical',
                'description': 'Chinese comics, vertical scroll'
            },
            {
                'name': 'Webtoon',
                'default_orientation': 'vertical',
                'description': 'Digital comics, vertical scroll'
            },
        ]
        
        for ct_data in content_types:
            ct, created = ContentType.objects.get_or_create(
                name=ct_data['name'],
                defaults={
                    'default_orientation': ct_data['default_orientation'],
                    'description': ct_data['description']
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created content type: {ct.name}')
                )