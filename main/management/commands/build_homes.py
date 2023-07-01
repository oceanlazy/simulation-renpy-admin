import random

from django.core.management.base import BaseCommand

from main.models import Character, Place, PlaceTransition


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write('Start')

        for char in Character.objects.filter(is_clone=False):
            if Place.objects.filter(owner=char, place_type='bedroom').exists():
                continue

            if char.settlement_id:
                bound_place = Place.objects.filter(
                    settlement=char.settlement, place_type='street'
                ).order_by('?').first()
                distance = round(random.uniform(0.3, 0.7), 2)
                title_base = f'{char.title}_{char.settlement.title}'
            else:
                bound_place = Place.objects.filter(
                    safety__gte=500,
                    beauty__gte=300,
                    settlement__isnull=True,
                    place_type='region'
                ).order_by('?').first()
                distance = round(random.uniform(0.5, 0.9), 2)
                title_base = f'{char.title}_{bound_place.title}'

            base_data = {'owner': char, 'settlement': char.settlement, 'beauty': 600, 'fertility': 100, 'safety': 1000}
            hallway = Place.objects.create(
                title=f'{title_base}_hallway', name='Hallway', place_type='hallway', **base_data
            )
            room = Place.objects.create(
                title=f'{title_base}_living_room', name='Living room', place_type='living_room', **base_data
            )
            bedroom = Place.objects.create(
                title=f'{title_base}_bedroom', name='Bedroom', place_type='bedroom', **base_data
            )
            dining = Place.objects.create(
                title=f'{title_base}_dining', name='Dining', place_type='dining', **base_data
            )
            entrance = Place.objects.create(
                title=f'{title_base}_entrance',
                name='Entrance',
                place_type='entrance',
                is_locked=True,
                lock_filters={'id__or': char.id, 'place_id__or': hallway.id},
                **base_data
            )

            PlaceTransition.objects.create(from_place=bound_place, to_place=entrance, distance=distance)
            PlaceTransition.objects.create(from_place=entrance, to_place=bound_place, distance=distance)
            for place in (entrance, room, bedroom, dining):
                distance = round(random.uniform(0.001, 0.01), 3)
                PlaceTransition.objects.create(from_place=place, to_place=hallway, distance=distance)
                PlaceTransition.objects.create(from_place=hallway, to_place=place, distance=distance)

            self.stdout.write(f'Created home for {char.title}')

        self.stdout.write('Done')
