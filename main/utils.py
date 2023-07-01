import re

from typing import Union
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.forms import ValidationError

PLAYER_ID = 16
PLACE_TYPE_CHOICES = (
    ('kitchen', 'Kitchen'),
    ('prison', 'Prison'),
    ('prison_cell', 'Prison cell'),
    ('region', 'Region'),
    ('settlement_gates', 'Settlement gates'),
    ('street', 'Street'),
    ('temple', 'Temple'),
    ('throne_room', 'Throne room'),
    ('entrance', 'Entrance'),
    ('hallway', 'Hallway'),
    ('living_room', 'Living room'),
    ('dining', 'Dining room'),
    ('bedroom', 'Bedroom')
)
HAIR_COLOR_CHOICES = (
    ('black', 'Black'),
    ('blonde', 'Blonde'),
    ('blue', 'Blue'),
    ('bold', 'Bold'),
    ('brunette', 'Brunette'),
    ('green', 'Green'),
    ('pink', 'Pink'),
    ('red', 'Red'),
    ('white', 'White')
)
HAIRSTYLE_CHOICES = (
    ('bold', 'Bold'),
    ('long', 'Long'),
    ('medium', 'Medium'),
    ('short', 'Short')
)
SKIN_COLOR_CHOICES = (
    ('black', 'Black'),
    ('blue', 'Blue'),
    ('bronze', 'Bronze'),
    ('yellow', 'Yellow'),
    ('white', 'White')
)
PLAN_STAGE_ORDER_CHOICES = (
    ('one', 'One'),
    ('two', 'Two'),
    ('three', 'Three'),
    ('four', 'Four'),
    ('five', 'Five'),
)
ROUTE_STATUS_CHOICES = (
    ('in_progress', 'In progress'),
    ('finished', 'Finished'),
    ('not_found', 'Not found'),
    ('locked', 'Locked'),
)

LABELS_VALUES = {
    100: 'min',
    200: 'lowest',
    300: 'low',
    400: 'below_average',
    500: 'average',
    600: 'above_average',
    700: 'high',
    800: 'very_high',
    900: 'highest',
    1000: 'max',
}

FILTER_V_REPLACEMENTS = {
    None: 'null',
    '_id': 'current',
    '_settlement_id': 'current',
    '_place_id': 'current',
    '_faction_id': 'current',
    '_position_id': 'current',
}


class DescMixin:
    def get_str(self: models.Model, is_count=True, is_name=True, title=None):
        items = []
        if is_name:
            items.append(f'{self.__class__.__name__}({self.id}): ')
        items.append(title or self.get_str_instance())  # noqa
        if is_count:
            items.append(f'({get_instance_relations_count(self)})')
        return ''.join(items)


def parse_filter(lookup):
    lookup_clear = lookup
    if '__or' in lookup and re.search(r'__or([0-9])?(a)?([0-9])?$', lookup):
        lookup_clear = lookup.rsplit('__', 1)[0]
    lookup_relations = lookup_clear.split('__')
    cmds = {'exact', 'ne', 'gte', 'gt', 'lte', 'lt', 'in', 'nin', 'isnull'} & set(lookup_relations)
    if cmds:
        cmd = cmds.pop()
        lookup_relations.remove(cmd)
    else:
        cmd = 'exact'
    field_name = lookup_relations.pop()
    return lookup_relations, field_name, cmd


def check_json_model_fields(data: Union[dict, list], data_fields: dict, is_validate=True, exclude=None):
    if not data:
        return data
    exclude_fields = ['relationship']
    if exclude:
        exclude_fields.extend(exclude)
    for k in data:
        if '_set' in k:
            continue
        relations, lookup, cmd = parse_filter(k)
        if relations:
            relation = relations[0]
            if relation not in data_fields:
                raise ValidationError(f'Relation not found: "{relation}"')
            if not data_fields[relation]['is_model']:
                raise ValidationError(f'Relation is not a model: "{relation}"')
            continue
        if lookup not in data_fields:
            if lookup in exclude_fields:
                continue
            raise ValidationError(f'Field not found: "{lookup}"')
        if data_fields[lookup]['is_model']:
            raise ValidationError(f'Field is model: "{lookup}". Use "{lookup}_id".')
        if is_validate:
            v = data[k]
            if not v or not isinstance(v, int):
                continue
            min_value = data_fields[lookup]['min']
            max_value = data_fields[lookup]['max']
            if min_value is not None and max_value is not None:
                if min_value > v:
                    raise ValidationError(f'"{lookup}" Must be greater then: {min_value}')
                if max_value < v:
                    raise ValidationError(f'"{lookup}" Must be less then: {max_value}')
    return data


def check_json_keys(outer_data, valid_data):
    errors = set(outer_data) - set(valid_data)
    if errors:
        raise ValidationError(f'Wrong keys: "{errors}"')
    return outer_data


def check_modifier(key, pos_neg_data, fields):
    data = pos_neg_data.get(key)
    if not data:
        return
    for attrs_type in ['max', 'min', 'avg']:
        attrs_type_data = data.get(attrs_type)
        if attrs_type_data:
            check_json_model_fields(attrs_type_data, fields, is_validate=False)
    attrs_exact_data = data.get('exact')
    if attrs_exact_data:
        check_json_model_fields([attrs_exact_data], fields, is_validate=False)
    return


def check_modifiers(data, fields):
    for pos_neg in ['positive', 'negative']:
        check_modifier(pos_neg, data, fields)
    return data


def check_characters_modifiers(data, fields):
    for pos_neg in ['positive', 'negative']:
        pos_neg_data = data.get(pos_neg)
        if not pos_neg_data:
            continue
        for own_other in ['own', 'other']:
            check_modifier(own_other, pos_neg_data, fields)
    return data


def get_desc_mod(mod_data):
    items = []
    for max_min_avg in ['max', 'min', 'avg']:
        max_min_avg_data = mod_data.get(max_min_avg)
        if not max_min_avg_data:
            continue
        items.append(max_min_avg)
        for attr in max_min_avg_data:
            items.append(attr)
    else:
        exact_data = mod_data.get('exact')
        if exact_data:
            items.append(exact_data)
    return '_'.join(items)


def get_desc_mods(mods, delimiter=', '):
    items = []
    for pos_neg in ['positive', 'negative']:
        pos_neg_data = mods.get(pos_neg)
        if not pos_neg_data:
            continue
        items_pos_neg = [pos_neg]
        if 'own' in pos_neg_data or 'other' in pos_neg_data:
            for own_other in ['own', 'other']:
                own_other_data = pos_neg_data.get(own_other)
                if not own_other_data:
                    continue
                items_pos_neg.append(own_other)
                desc_mod_item = get_desc_mod(own_other_data)
                if desc_mod_item:
                    items_pos_neg.append(desc_mod_item)
        else:
            desc_mod_item = get_desc_mod(pos_neg_data)
            if desc_mod_item:
                items_pos_neg.append(desc_mod_item)
        items.append('_'.join(items_pos_neg))
    return delimiter.join(items)


def get_fields_data(model):
    data = {}
    for field in model._meta.fields:  # noqa
        field_data = {'min': None, 'max': None}
        if isinstance(field, models.PositiveIntegerField):
            field_data['min'] = 0
        for validator in field.validators:
            if isinstance(validator, MinValueValidator):
                field_data['min'] = validator.limit_value
            elif isinstance(validator, MaxValueValidator):
                field_data['max'] = validator.limit_value
        field_data['is_model'] = field.is_relation
        data[field.name] = field_data
        if field.name != field.attname:
            data[field.attname] = {k: v for k, v in field_data.items()}
            data[field.attname]['is_model'] = False
    return data


def get_time_seconds(t, days=0):
    return days * 86400 + t.hour * 3600 + t.minute * 60 + t.second


def get_instance_relations_count(instance):
    rels_count = 0
    for related in instance._meta.related_objects:  # noqa
        rels_count += related.field.model.objects.filter(**{related.remote_field.attname: instance.id}).count()
    return rels_count


def get_filter_v_replace(filter_v):
    if filter_v is None:
        return FILTER_V_REPLACEMENTS[None]
    if filter_v.startswith('_second_char'):
        filter_v_replaced = FILTER_V_REPLACEMENTS.get(filter_v[12:])
        if filter_v_replaced:
            return f'second_char_{filter_v_replaced}'
    return FILTER_V_REPLACEMENTS.get(filter_v, filter_v)


def get_filter_v_display(filter_v):
    if isinstance(filter_v, str) or filter_v is None:
        return get_filter_v_replace(filter_v)
    if isinstance(filter_v, list):
        return '_'.join([str(v) for v in filter_v])
    if isinstance(filter_v, dict):
        return '_'.join(['{}_{}'.format(k, get_filter_v_replace(v)) for k, v in filter_v.items()])
    return filter_v


def get_filter_place_desc(filter_k, filter_v):
    filter_v_result = get_filter_v_display(filter_v)
    filter_k_result = 'place' if filter_k.startswith('id') else filter_k.replace('__', '_')
    return f'{filter_k_result}_{filter_v_result}'.lower()
