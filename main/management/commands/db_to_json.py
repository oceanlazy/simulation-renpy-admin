import inspect
import json

from datetime import date, time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Count, ForeignKey, IntegerField
from django.db.models.base import ModelBase
from django.db.models.fields import NOT_PROVIDED

from main import models


def dump_value(value):
    if isinstance(value, (str, int, float, bool, dict, list)) or value is None:
        return value
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    if isinstance(value, time):
        return value.strftime('%H:%M:%S')
    raise ValueError(f'Wrong dump value type: {type(value)}')


def get_attrs_range(model):
    data = {}
    for instance in model.objects.all():
        for k, v in vars(instance).items():
            if not isinstance(v, int):
                continue
            data_validators = {}
            for validator in getattr(model, k).field.validators:
                if isinstance(validator, MinValueValidator):
                    data_validators['min'] = validator.limit_value
                elif isinstance(validator, MaxValueValidator):
                    data_validators['max'] = validator.limit_value
            if data_validators:
                data[k] = data_validators
    return data


def get_objects(model):
    return {
        instance.id: {
            k: dump_value(v) for k, v in vars(instance).items() if k != '_state'
        } for instance in model.objects.all()
    }


def get_model_fields(model):
    return [f.attname if isinstance(f, ForeignKey) else f.name for f in model._meta.fields]  # noqa


def get_model_effects_fields(model):
    return [f.name for f in model._meta.fields if isinstance(f, IntegerField) if f.name != 'id']  # noqa


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write('Start')
        if settings.EXPORT_DIR.is_dir():
            db_path = settings.EXPORT_DIR / 'db'
        else:
            self.stdout.write('Export directory not found')
            db_path = settings.BASE_DIR / 'db'
        db_path.mkdir(exist_ok=True)

        chars_places = dict(models.Character.objects.values(
            'place_id'
        ).annotate(
            count=Count('place_id')
        ).values_list(
            'place_id', 'count'
        ))
        places = []
        for place in models.Place.objects.filter(id__in=chars_places):
            place.population = chars_places[place.id]
            places.append(place)
        models.Place.objects.update(population=0)
        models.Place.objects.bulk_update(places, ['population'])

        for name, klass in inspect.getmembers(models, predicate=lambda cls: isinstance(cls, ModelBase)):
            klass_meta = klass._meta  # noqa

            if klass_meta.abstract:
                continue
            with open(db_path / f'{klass_meta.db_table}.json', 'w') as f:
                data = {
                    'name': name,
                    'mtm_data': {},
                    'mto_data': {},
                    'set_data': {},
                    'time_fields': [],
                    'objects': get_objects(klass),
                    'objects_fields': get_model_fields(klass),
                    'objects_effects_fields': get_model_effects_fields(klass),
                    'attrs_ranges': get_attrs_range(klass),
                    'defaults': {}
                }

                for rel in klass_meta.many_to_many:
                    through_model = rel.remote_field.through
                    with open(db_path / f'{through_model._meta.db_table}.json', 'w') as f_through:  # noqa
                        f_through.write(json.dumps({
                            'name': through_model.__name__,
                            'set_data': {},
                            'mtm_data': {},
                            'mto_data': {},
                            'time_fields': [],
                            'objects': get_objects(through_model),
                            'objects_fields': get_model_fields(through_model),
                            'objects_effects_fields': [],
                            'attrs_ranges': {},
                            'defaults': {}
                        }, indent=4))

                    data['mtm_data'][rel.name] = {
                        'model': rel.related_model.__name__,
                        'through': through_model.__name__,
                        'from_id': rel.m2m_column_name(),
                        'target_id': rel.m2m_reverse_name()
                    }

                for field in klass_meta.fields:
                    if field.many_to_one or field.one_to_one:
                        data['mto_data'][field.name] = {'model': field.related_model.__name__, 'from_id': field.attname}
                    if field.default is not NOT_PROVIDED:
                        default = field.default
                        data['defaults'][field.name] = default() if callable(default) else default
                    elif not field.is_relation:
                        data['defaults'][field.name] = None
                    if field.__class__.__name__ == 'TimeField':
                        data['time_fields'].append(field.attname)

                for rel in klass_meta.related_objects:
                    if rel.one_to_many and not rel.hidden:
                        data['set_data']['{}_set'.format(rel.related_name or rel.name)] = {
                            'model': rel.related_model.__name__, 'target_id': rel.field.attname
                        }

                f.write(json.dumps(data, indent=4))

        self.stdout.write(f'Saved to: "{db_path}"')
