from django.core.management.base import BaseCommand

from main.models import Character, CharacterRelationship


def get_opinion(first, second, is_negative=True, is_difference=True, first_mod=.5, second_mod=1.5):
    opinion = 0
    if first > 500 and second > 500:
        opinion = (first * first_mod + second * second_mod) - 1000
    elif is_negative and first < 500 and second < 500:
        opinion = 1000 - (first * first_mod + second * second_mod)
    elif is_difference and (first > 500 > second or first < 500 < second):
        opinion = -abs(first - second)
    else:
        return opinion
    return opinion / 2  # values should be in range 0-500


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write('Start')

        chars = list(Character.objects.filter(is_original=True))
        chars_relations_pks = {
            (r['from_character_id'], r['to_character_id']): r for r in CharacterRelationship.objects.values()
        }
        relations_create = []
        relations_update = []

        for char_from in chars:
            for char_to in chars:
                if char_from.pk == char_to.pk:
                    continue

                opinion = 500
                opinion += get_opinion(char_from.intelligence, char_to.intelligence) * .2
                opinion += get_opinion(char_from.pride, char_to.pride) * .2

                if opinion > 1000:
                    opinion = 1000
                elif opinion < 100:
                    opinion = 100
                opinion = int(opinion)

                self.stdout.write(f'{char_from.title} -> {char_to.title} = {opinion}')

                c_relationship = CharacterRelationship(
                    from_character_id=char_from.pk, to_character_id=char_to.pk, value=opinion
                )
                chars_relations_pks_key = (char_from.pk, char_to.pk)
                if chars_relations_pks_key in chars_relations_pks:
                    if chars_relations_pks[chars_relations_pks_key]['value'] != opinion:
                        c_relationship.id = chars_relations_pks[(char_from.pk, char_to.pk)]['id']
                        relations_update.append(c_relationship)
                else:
                    relations_create.append(c_relationship)

        if relations_create:
            CharacterRelationship.objects.bulk_create(relations_create, ignore_conflicts=True)
            self.stdout.write(f'Created {len(relations_create)} objects')
        if relations_update:
            CharacterRelationship.objects.bulk_update(relations_update, fields=['value'])
            self.stdout.write(f'Updated {len(relations_update)} objects')
        if not relations_create and not relations_update:
            self.stdout.write('No changes')
        self.stdout.write('Done')
