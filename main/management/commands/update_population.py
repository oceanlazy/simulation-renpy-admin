from django.core.management.base import BaseCommand

from main.models import Place


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write('Start')
        places = []
        for place in Place.objects.all():
            place.population = place.character_set.count()
            places.append(place)
        Place.objects.bulk_update(places, ['population'])
        self.stdout.write('Done')
