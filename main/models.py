from datetime import timedelta

from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from main.utils import (
    DescMixin,
    HAIR_COLOR_CHOICES,
    HAIRSTYLE_CHOICES,
    LABELS_VALUES,
    PLACE_TYPE_CHOICES,
    PLAN_STAGE_ORDER_CHOICES,
    ROUTE_STATUS_CHOICES,
    SKIN_COLOR_CHOICES,
    get_desc_mods,
    get_fields_data,
    get_filter_place_desc,
    get_filter_v_display,
    get_instance_relations_count
)


class CharacterDataFilters(models.Model, DescMixin):
    title = models.CharField('Title', max_length=100, blank=True)
    is_interrupting = models.BooleanField(
        default=False, blank=True, help_text='Used for effects, interrupt plan if filters failed.'
    )
    filters = models.JSONField('Character filters', default=dict, blank=True)
    plan_points_mods = models.JSONField(
        verbose_name='Points plan modifiers',
        help_text='Example: {"positive": {"other": {"max": ["sleep", "health"], "exact": "energy"}}}. '
                  'Options: positive/negative, own/other, max/min/avg/exact.',
        default=dict,
        blank=True
    )
    acceptance_points_base = models.JSONField(
        verbose_name='Points acceptance base',
        help_text='Base for acceptance points. '
                  'Example: {"positive": {"other": {"max": ["sleep", "health"], "exact": "energy"}}}.',
        default=dict,
        blank=True
    )
    acceptance_points_mods = models.JSONField(
        verbose_name='Modifiers for acceptance points',
        help_text='Example: {"positive": {"other": {"max": ["sleep", "health"], "exact": "energy"}}}. '
                  'Options: positive/negative, own/other, max/min/avg/exact. '
                  'Calculating: points_base * mod * 2 * mod_value',
        default=dict,
        blank=True
    )
    faction_opinion_min = models.PositiveSmallIntegerField(
        verbose_name='Faction opinion min',
        validators=[MinValueValidator(100), MaxValueValidator(1000)],
        blank=True,
        null=True
    )
    faction_opinion_max = models.PositiveSmallIntegerField(
        'Faction opinion max', validators=[MinValueValidator(100), MaxValueValidator(1000)], blank=True, null=True
    )
    relationships_min = models.PositiveSmallIntegerField(
        verbose_name='Personal relationships min',
        validators=[MinValueValidator(100), MaxValueValidator(1000)],
        blank=True,
        null=True
    )
    relationships_max = models.PositiveSmallIntegerField(
        verbose_name='Personal relationships max',
        validators=[MinValueValidator(100), MaxValueValidator(1000)],
        blank=True,
        null=True
    )
    acceptance_points_min = models.PositiveSmallIntegerField(
        'Acceptance points min', validators=[MinValueValidator(100), MaxValueValidator(1000)], blank=True, null=True
    )
    acceptance_points_max = models.PositiveSmallIntegerField(
        'Acceptance points max', validators=[MinValueValidator(100), MaxValueValidator(1000)], blank=True, null=True
    )
    acceptance_points_mod_value = models.FloatField(
        validators=[MaxValueValidator(10)],
        help_text='Multiply effects_mods. Range: 0-10. Default: 1.',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.get_str(is_name=False)

    def get_str_instance(self):
        if self.title:
            return self.title

        items = []

        for filter_k in self.filters:
            filter_v = self.filters[filter_k]

            if filter_k.startswith('gender'):
                items.append(filter_v)
                continue

            if set(filter_k.split('__')) & set(char_attrs_ranged):
                filter_text = ''
                for label_value in LABELS_VALUES:
                    if filter_v >= label_value:
                        filter_text = LABELS_VALUES[label_value]
                    else:
                        break
                if filter_text:
                    filter_v = filter_text
            if isinstance(filter_v, list):
                filter_v = '_'.join(filter_v)
            elif isinstance(filter_v, str):
                if filter_v.startswith('_'):
                    filter_v = filter_v[1:]
            items.append(f'{filter_k.replace("__", "_")}_{filter_v}')

        if self.is_interrupting:
            items.append('is_interrupting')

        return '__'.join(items).lower()


class CharacterDataEffects(models.Model):
    title = models.CharField(max_length=100, blank=True)
    effects = models.JSONField(help_text='Example: {"energy": 50, "health": 10, "mood": 15}', default=dict, blank=True)
    effects_max = models.JSONField(help_text='Example: {"energy": 300, "mood": 800}', default=dict, blank=True)
    effects_mods = models.JSONField(
        verbose_name='Effects modifiers from character attrs',
        help_text='Example: {"positive": {"other": {"max": ["sleep", "health"], "exact": "energy"}}} '
                  'Options: positive/negative, own/other, max/min/avg/exact. '
                  'Calculating: attr_value/1000+0.5 = results in range 0.6-1.5. '
                  'Example: attr value = 800. Positive = 1.3, Negative = 0.7.',
        default=dict,
        blank=True
    )
    effects_mods_value = models.FloatField(
        validators=[MaxValueValidator(10)],
        help_text='Multiply effects_mods. Range: 0-10. Default: 1.',
        blank=True,
        null=True
    )
    effects_place_mods = models.JSONField(
        verbose_name='Effects modifiers from place attrs',
        help_text='Example: {"positive": {"max": ["safety", "beauty"], "exact": "fertility"}} '
                  'Options: positive/negative, max/min/avg/exact.',
        default=dict,
        blank=True
    )
    settlement_effects = models.JSONField(default=dict, blank=True)
    settlement_effects_max = models.JSONField(default=dict, blank=True)
    place_settlement_effects = models.JSONField(default=dict, blank=True)
    place_settlement_effects_max = models.JSONField(default=dict, blank=True)
    needs_mods = models.JSONField(
        help_text='Example: {"energy": 1, "mood": 1}. Default is 1.', default=dict, blank=True
    )
    relationships_effects = models.FloatField(blank=True, null=True)
    relationships_effects_max = models.PositiveSmallIntegerField(blank=True, null=True)
    relationships_effects_min = models.PositiveSmallIntegerField(blank=True, null=True)

    def __str__(self):
        if self.title:
            return f'{self.title} ({get_instance_relations_count(self)})'
        items = [
            ', '.join(['{}({})'.format(k, get_filter_v_display(v)) for k, v in effects.items()])
            for effects in [self.effects, self.settlement_effects, self.place_settlement_effects] if effects
        ]
        if self.effects_mods:
            items.append(get_desc_mods(self.effects_mods))
        if self.effects_place_mods:
            items.append(get_desc_mods(self.effects_place_mods))
        if self.relationships_effects:
            items_sec = [f'relationships({self.relationships_effects}']
            if self.relationships_effects_min or self.relationships_effects_max:
                items_sec.append(', {}-{}'.format(
                    self.relationships_effects_min or 100, self.relationships_effects_max or 1000
                ))
            items_sec.append(')')
            items.append(''.join(items_sec))
        if self.needs_mods:
            items.append(f"needs: {', '.join(['{}({})'.format(k, v) for k, v in self.needs_mods.items()])}")  # noqa
        return f'{", ".join(items)} ({get_instance_relations_count(self)})'


class CharacterDataPlanFilters(models.Model, DescMixin):
    title = models.CharField('Title', max_length=100, blank=True)
    filters = models.JSONField(
        verbose_name='Plan filters',
        help_text='Example: {"is_char_available": true, "id__nin": ["relax", "relax_home"]}',
        default=dict
    )
    is_random_weighted = models.BooleanField(default=False, help_text='More points more chances.')

    def __str__(self):
        return self.get_str(is_name=False)

    def get_str_instance(self):
        if self.title:
            return self.title
        items = []
        for filter_k in self.filters:
            filter_v = self.filters[filter_k]
            if filter_k == 'id':
                items.append(Plan.objects.get(id=filter_v).title)
            elif filter_k == 'id__in':
                items.extend(Plan.objects.filter(id__in=filter_v).values_list('title', flat=True))
            elif filter_k == 'id__ne':
                items.append(f'any_except_{filter_v}')
            elif filter_k == 'id__nin':
                values = Plan.objects.filter(id__in=filter_v).values_list('title', flat=True)
                items.append(f'any_except_{"_".join(values)}')
            else:
                items.append(f'{filter_k}_{str(filter_v).lower()}')
        s = '__'.join(items)
        if self.is_random_weighted:
            s = f'{s}, random points'
        return s


class Plan(models.Model):
    stages = ('one', 'two', 'three', 'four', 'five')

    title = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=50, blank=True)
    is_char_available = models.BooleanField('Is char available', default=False)
    is_player_available = models.BooleanField('Is player available', default=False)
    is_encounter = models.BooleanField(default=False)
    is_route = models.BooleanField(
        default=False, help_text='Will activate for all characters every time when they change location.'
    )
    is_ask_player = models.BooleanField(default=True, help_text='Ask player to be second if player is target.')
    is_always_pause = models.BooleanField('Is always time pause', default=False)
    is_first_pause = models.BooleanField('Is first char pause', default=True)
    is_second_pause = models.BooleanField('Is second char pause', default=False)
    is_break_second = models.BooleanField('Break second char plan', default=False, help_text='Overload on finish logic')
    is_important_event = models.BooleanField(default=False)
    is_ignore_event = models.BooleanField(default=False)
    time_pause = models.FloatField('Pause before the next attempt in minutes', blank=True, null=True)
    min_points = models.PositiveSmallIntegerField(
        'Minimum points', default=101, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )
    on_finish_first = models.CharField(
        choices=(('next_stage', 'Next stage'), ('break', 'Break')),
        default='next_stage',
        max_length=10,
        blank=True
    )
    on_finish_second = models.CharField(
        choices=(('next_stage', 'Next stage'), ('break', 'Break')),
        max_length=10,
        blank=True
    )
    event_desc = models.CharField(max_length=255, blank=True)
    ask_player_desc = models.CharField(max_length=255, blank=True)
    beginning_text = models.CharField(max_length=255, blank=True)
    filters = models.ForeignKey('PlanFilters', models.DO_NOTHING, related_name='plan_filters', blank=True, null=True)
    one = models.ForeignKey('Stage', models.DO_NOTHING, related_name='stage_one')
    two = models.ForeignKey('Stage', models.SET_NULL, blank=True, null=True, related_name='stage_two')
    three = models.ForeignKey('Stage', models.SET_NULL, blank=True, null=True, related_name='stage_three')
    four = models.ForeignKey('Stage', models.SET_NULL, blank=True, null=True, related_name='stage_four')
    five = models.ForeignKey('Stage', models.SET_NULL, blank=True, null=True, related_name='stage_five')

    def __str__(self):
        return self.title


class Stage(models.Model):
    title = models.CharField(max_length=50, blank=True)
    effects = models.ForeignKey('PlanEffects', models.SET_NULL, blank=True, null=True)
    filters = models.ForeignKey('PlanFilters', models.SET_NULL, blank=True, null=True)
    filters_plan_set = models.ForeignKey('PlanSetFilters', models.SET_NULL, blank=True, null=True)
    filters_place = models.ForeignKey('PlanPlaceFilters', models.SET_NULL, blank=True, null=True)
    lock = models.ForeignKey('PlanLock', models.SET_NULL, blank=True, null=True)
    plan_pause = models.ForeignKey(
        'PlanPause', models.SET_NULL, blank=True, null=True, help_text='Ignoring if stage is optional.'
    )
    is_optional = models.BooleanField(default=False, blank=True)
    time_pause = models.FloatField(
        'Pause minutes', blank=True, null=True, help_text='If stage failed. "-1" will disable plan.'
    )

    def __str__(self):
        cache_key = f'{self.__class__.__name__}_{self.id}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        if self.effects_id:
            items = [
                f'{self.effects.__class__.__name__}({self.effects.id}): ', self.title or self.effects.get_str_instance()
            ]
            if not self.title:
                if self.filters_plan_set_id:
                    items.append(', updatable')
                if self.filters_id:
                    items.append(', filtered')
                if self.is_optional:
                    items.append(', optional')
            items.append(f'({get_instance_relations_count(self)})')
            value = ''.join(items)
            cache.set(cache_key, value)
            return value

        for field in ['filters_place', 'lock', 'filters_plan_set', 'plan_pause', 'filters']:
            instance = getattr(self, field)
            if not instance:
                continue
            items = [instance.get_str(is_count=False, title=self.title)]
            if not self.title:
                if field != 'filters' and self.filters_id:
                    items.append(', filters')
                if self.is_optional:
                    items.append(', optional')
                if self.time_pause:
                    items.append(', time pause')
            items.append(f'({get_instance_relations_count(self)})')
            value = ''.join(items)
            cache.set(cache_key, value)
            return value

        if self.filters_id:
            value = self.filters.get_str()
            cache.set(cache_key, value)
            return value

        return 'empty'


class PlanFilters(models.Model, DescMixin):
    first_character = models.ForeignKey(
        'CharacterDataFilters', models.SET_NULL, blank=True, null=True, related_name='plan_filters_first_character'
    )
    second_character = models.ForeignKey(
        'CharacterDataFilters', models.SET_NULL, blank=True, null=True, related_name='plan_filters_second_character'
    )
    time_from = models.TimeField('Time to start', blank=True, null=True)
    time_from_seconds = models.PositiveIntegerField('Time to finish seconds', blank=True, null=True, editable=False)
    time_to = models.TimeField('Time to finish', blank=True, null=True)
    time_to_seconds = models.PositiveIntegerField('Time to finish seconds', blank=True, null=True, editable=False)
    time_min = models.TimeField('Stay in place min', blank=True, null=True)
    time_min_seconds = models.PositiveSmallIntegerField('Stay in place min seconds', null=True, editable=False)
    time_max = models.TimeField('Stay in place max', blank=True, null=True)
    time_max_seconds = models.PositiveSmallIntegerField('Stay in place max seconds', null=True, editable=False)
    is_time_points = models.BooleanField('Is day time influence on points', default=False)
    is_group = models.BooleanField(
        default=True, blank=True, help_text='Disable to not create a group but keep second char filter'
    )

    def __str__(self):
        cache_key = f'{self.__class__.__name__}_{self.id}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        value = self.get_str(is_name=False)
        cache.set(cache_key, self.get_str(is_name=False))
        return value

    def get_str_instance(self):
        items = []
        if self.first_character_id or self.second_character_id:
            items.append(''.join([
                self.first_character.get_str(is_name=False, is_count=False) if self.first_character_id else '',
                (' > ' if self.is_group else ' | ') if self.first_character_id and self.second_character_id else '',
                self.second_character.get_str(is_name=False, is_count=False) if self.second_character_id else ''
            ]))
        if self.time_from:
            items.append(f'from {self.time_from}')
        if self.time_to:
            items.append(f'to {self.time_to}')
        if self.time_min:
            items.append(f'min: {self.time_min}')
        if self.time_max:
            items.append(f'max: {self.time_max}')
        return ' '.join(items)


class PlanEffectsSet(models.Model, DescMixin):
    title = models.CharField('Title', max_length=50, unique=True)
    one = models.ForeignKey('CharacterDataEffects', models.DO_NOTHING, related_name='effects_set_one')
    two = models.ForeignKey(
        'CharacterDataEffects', models.SET_NULL, blank=True, null=True, related_name='effects_set_two'
    )
    three = models.ForeignKey(
        'CharacterDataEffects', models.SET_NULL, blank=True, null=True, related_name='effects_set_three'
    )
    four = models.ForeignKey(
        'CharacterDataEffects', models.SET_NULL, blank=True, null=True, related_name='effects_set_four'
    )
    five = models.ForeignKey(
        'CharacterDataEffects', models.SET_NULL, blank=True, null=True, related_name='effects_set_five'
    )

    def __str__(self):
        return self.get_str(is_name=False)

    def get_str_instance(self):
        return self.title


class PlanEffects(models.Model, DescMixin):
    first_character = models.ForeignKey(
        'PlanEffectsSet', models.SET_NULL, blank=True, null=True, related_name='plan_effects_set_first_character'
    )
    second_character = models.ForeignKey(
        'PlanEffectsSet', models.SET_NULL, blank=True, null=True, related_name='plan_effects_set_second_character'
    )
    is_instant = models.BooleanField(default=False)

    def __str__(self):
        return self.get_str(is_name=False)

    def get_str_instance(self):
        items = []
        if self.first_character_id and self.second_character_id:
            items.append('{} > {}'.format(
                self.first_character.get_str(is_count=False, is_name=False),
                self.second_character.get_str(is_count=False, is_name=False)
            ))
        elif self.first_character_id:
            items.append(self.first_character.get_str(is_count=False, is_name=False))
        elif self.second_character_id:
            items.append('second: {}'.format(self.second_character.get_str(is_count=False, is_name=False)))
        return ''.join(items)


class PlanSetFilters(models.Model, DescMixin):
    first_character = models.ForeignKey(
        'CharacterDataPlanFilters', models.SET_NULL, blank=True, null=True, related_name='plan_filters_first'
    )
    second_character = models.ForeignKey(
        'CharacterDataPlanFilters', models.SET_NULL, blank=True, null=True, related_name='plan_filters_second'
    )

    def __str__(self):
        return self.get_str(is_name=False)

    def get_str_instance(self):
        items = []
        if self.first_character_id:
            items.append(str(self.first_character.get_str(is_name=False, is_count=False)))
        if self.second_character_id:
            items.append(' > ' if self.first_character_id else 'second: ')
            items.append(str(self.second_character.get_str(is_name=False, is_count=False)))
        return ''.join(items) or 'empty'


class PlanPlaceFilters(models.Model, DescMixin):
    title = models.CharField('Title', max_length=50, blank=True)
    is_random = models.BooleanField(default=False)
    is_nearest = models.BooleanField(default=False, help_text='Overrides distance penalty.')
    is_teleportation = models.BooleanField(default=False)
    distance_penalty = models.PositiveSmallIntegerField(null=True, blank=True, default=10, help_text='Per kilometer.')
    filters = models.JSONField('Place filters', default=dict, blank=True)
    attrs_importance = models.JSONField(
        verbose_name='Place stats importance',
        help_text='Example: {"beauty": 0.3, "fertility": 0.3, "safety": 0.4}',
        default=dict,
        blank=True
    )
    max_distance = models.PositiveSmallIntegerField('Maximum distance(including)', blank=True, null=True)

    def __str__(self):
        return self.get_str(is_name=False)

    def get_str_instance(self):
        if self.title:
            return self.title

        items = []

        for filter_k in self.filters:
            filter_v = self.filters[filter_k]

            item = get_filter_place_desc(filter_k, filter_v)
            if item:
                items.append(item)
                continue

            for attr_name in ['safety', 'beauty', 'fertility']:
                if not filter_k.startswith(attr_name):
                    continue
                label = ''
                for label_value in LABELS_VALUES:
                    if filter_v >= label_value:
                        label = LABELS_VALUES[label_value]
                    else:
                        break
                condition = ''
                for condition_name in ['gt', 'gte', 'lt', 'lte']:
                    if f'__{condition_name}' in filter_k:
                        condition = f'_{condition_name}'
                        break
                items.append(f'{attr_name}{condition}_{label}')
                break

        items = ['__'.join(items)]
        if self.max_distance:
            items.append(f', {self.max_distance}km')
        if self.is_random:
            items.append(', random')
        if self.is_nearest:
            items.append(', nearest')
        if self.is_teleportation:
            items.append(', teleportation')

        return ''.join(items)


class PlanLock(models.Model, DescMixin):
    title = models.CharField('Title', max_length=50, blank=True)
    close_filters = models.JSONField(
        verbose_name='Lock filters',
        help_text='Example: {"id": "_place_id"}',
        default=dict,
        blank=True
    )
    open_filters = models.JSONField(
        verbose_name='Open filters',
        help_text='Example: {"position__title": "soldier"}',
        default=dict,
        blank=True
    )

    def __str__(self):
        return self.get_str(is_name=False)

    def get_str_instance(self):
        if self.title:
            return self.title
        items = []
        for name, filters in (('lock', self.close_filters), ('unlock', self.open_filters)):
            items_filters = []
            for filter_k in filters:
                filter_v = filters[filter_k]
                item = get_filter_place_desc(filter_k, filter_v)
                if item:
                    items_filters.append(item)
                    continue
            if items_filters:
                items.append(f'{name}_{"_".join(items_filters)}')
        return ', '.join(items)


class PlanPause(models.Model, DescMixin):
    first = models.JSONField(default=dict, blank=True)
    second = models.JSONField(default=dict, blank=True, help_text='Example: {"relax": 30, "talk": 30}')

    def __str__(self):
        return self.get_str(is_name=False)

    def get_str_instance(self):
        items = []
        for data, char_letter in ((self.first, 'f'), (self.second, 's')):
            items_char = ['{}_{}'.format(title, pause) for title, pause in data.items()]
            if items_char:
                items.append('{}: {}'.format(char_letter, '__'.join(items_char)))
        return ', '.join(items)


class Character(models.Model):
    title = models.CharField(max_length=50, unique=True)
    is_original = models.BooleanField(default=True, blank=True)
    is_chained = models.BooleanField(default=False, blank=True)
    is_clone = models.BooleanField(default=False, help_text='Will not change original if cloned.')
    color_name = models.CharField('Dialog name color', default='FFFFFF', max_length=7)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, blank=True)
    gender = models.CharField(choices=(('male', 'Male'), ('female', 'Female')), default='male', max_length=10)
    kind = models.CharField(choices=(('human', 'Human'), ('monster', 'Monster')), default='human', max_length=10)
    skin_color = models.CharField(choices=SKIN_COLOR_CHOICES, default='white', max_length=10)
    hair_color = models.CharField(choices=HAIR_COLOR_CHOICES, default='black', max_length=10)
    hairstyle = models.CharField(choices=HAIRSTYLE_CHOICES, default='short', max_length=10)
    bio = models.TextField('Biography', blank=True, max_length=400)
    plan_data = models.ForeignKey('PlanData', models.SET_NULL, blank=True, null=True)
    place = models.ForeignKey('Place', models.SET_NULL, null=True, blank=True)
    settlement = models.ForeignKey('Settlement', models.SET_NULL, blank=True, null=True)
    position = models.ForeignKey('SettlementPosition', models.SET_NULL, blank=True, null=True)
    faction = models.ForeignKey('Faction', models.PROTECT, default=2)
    relationships = models.ManyToManyField('self', through='CharacterRelationship', blank=True)
    gold = models.PositiveIntegerField(default=100)
    health = models.PositiveSmallIntegerField(
        default=1000, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )
    energy = models.PositiveSmallIntegerField(
        default=1000, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )
    sleep = models.PositiveSmallIntegerField(
        default=1000, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )
    mood = models.PositiveSmallIntegerField(
        default=500, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )
    fighting = models.PositiveSmallIntegerField(
        default=100, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )
    magic = models.PositiveSmallIntegerField(
        default=100, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )
    intelligence = models.PositiveSmallIntegerField(
        default=500, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )
    pride = models.PositiveSmallIntegerField(
        default=500, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )

    def __str__(self):
        return '{}{}'.format(self.first_name, f' {self.last_name}' if self.last_name else '')


class EventLog(models.Model):
    is_important = models.BooleanField(default=False)
    timestamp = models.PositiveIntegerField()
    plan = models.ForeignKey('Plan', models.SET_NULL, null=True)
    first_character = models.ForeignKey(
        'Character', models.SET_NULL, related_name='event_log_first_character', null=True
    )
    second_character = models.ForeignKey(
        'Character', models.SET_NULL, related_name='event_log_second_character', blank=True, null=True
    )
    place = models.ForeignKey('Place', models.SET_NULL, null=True)

    def __str__(self):
        return '{}: {}{} - {}'.format(
            timedelta(seconds=self.timestamp),
            self.first_character.title,
            '({})'.format(self.second_character.title) if self.second_character else '',
            self.plan.title
        )


class PlanData(models.Model):
    plan = models.ForeignKey(Plan, models.CASCADE)
    plan_stage = models.CharField('Plan stage order', max_length=10, default='one', choices=PLAN_STAGE_ORDER_CHOICES)
    first_character = models.ForeignKey(Character, models.CASCADE, related_name='plan_data_first_character')
    second_character = models.ForeignKey(
        Character, models.SET_NULL, blank=True, null=True, related_name='plan_data_second_character'
    )
    first_previous = models.ForeignKey(
        'self', models.SET_NULL, blank=True, null=True, related_name='plan_data_first_previous'
    )
    second_previous = models.ForeignKey(
        'self', models.SET_NULL, blank=True, null=True, related_name='plan_data_second_previous'
    )
    first_route = models.ForeignKey(
        'Route', models.SET_NULL, blank=True, null=True, related_name='plan_data_first_route'
    )
    second_route = models.ForeignKey(
        'Route', models.SET_NULL, blank=True, null=True, related_name='plan_data_second_route'
    )

    def __str__(self):
        if self.second_character_id:
            return '{} and {}'.format(self.first_character.title, self.second_character.title)
        return self.first_character.title


class CharacterRelationship(models.Model):
    class Meta:
        unique_together = ['from_character', 'to_character']

    from_character = models.ForeignKey(Character, models.CASCADE, 'relationship_from_character')
    to_character = models.ForeignKey(Character, models.CASCADE, 'relationship_to_character')
    value = models.PositiveSmallIntegerField(
        'Value', default=500, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )

    def __str__(self):
        return f'Relation: {self.from_character} > {self.to_character} = {self.value}'


class Faction(models.Model):
    title = models.CharField('Title', max_length=50, unique=True)
    name = models.CharField('Name', max_length=50)
    relationships = models.ManyToManyField('self', through='FactionRelationship')

    def __str__(self):
        return self.title


class FactionRelationship(models.Model):
    class Meta:
        unique_together = ['from_faction', 'to_faction']

    from_faction = models.ForeignKey(Faction, models.CASCADE, 'relationship_from_faction')
    to_faction = models.ForeignKey(Faction, models.CASCADE, 'relationship_to_faction')
    value = models.PositiveSmallIntegerField(
        default=500, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )

    def __str__(self):
        return f'Relation: {self.from_faction} > {self.to_faction} = {self.value}'


class Route(models.Model):
    first_character = models.ForeignKey('Character', models.CASCADE, related_name='route_first_character')
    second_character = models.ForeignKey(
        'Character', models.CASCADE, blank=True, null=True, related_name='route_character_second'
    )
    start_place = models.ForeignKey('Place', models.SET_NULL, blank=True, null=True, related_name='route_start_place')
    is_targeted = models.BooleanField(
        default=False,
        blank=True,
        help_text='The route with single possible place to finish, used to disable bypassing the locked place',
        editable=False
    )
    route_distance = models.FloatField('Route distance', default=0.0)
    distance_passed = models.FloatField('Distance passed', default=0.0)
    places = models.JSONField(default=dict)
    status = models.CharField(
        choices=ROUTE_STATUS_CHOICES,
        default='in_progress',
        max_length=11,
        blank=True
    )


# Places
class Place(models.Model):
    title = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=50)
    is_locked = models.BooleanField(default=False)
    place_type = models.CharField(choices=PLACE_TYPE_CHOICES, default='region', max_length=50)
    settlement = models.ForeignKey('Settlement', models.SET_NULL, blank=True, null=True)
    owner = models.ForeignKey(Character, models.CASCADE, blank=True, null=True, related_name='place_owner')
    beauty = models.PositiveSmallIntegerField(default=500, validators=[MinValueValidator(100), MaxValueValidator(1000)])
    fertility = models.PositiveSmallIntegerField(
        default=100, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )
    safety = models.PositiveSmallIntegerField(
        default=1000, validators=[MinValueValidator(100), MaxValueValidator(1000)]
    )
    population = models.PositiveSmallIntegerField(blank=True, default=0)
    lock_filters = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.title


class Settlement(models.Model):
    title = models.CharField('Title', max_length=50, unique=True)
    gold = models.PositiveIntegerField('Gold', default=1000)
    positions = models.ManyToManyField('SettlementPosition', blank=True)
    is_positions_set_required = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class PlaceTransition(models.Model):
    class Meta:
        unique_together = ('from_place', 'to_place')

    from_place = models.ForeignKey('Place', models.CASCADE, related_name='from_place', related_query_name='from_place')
    to_place = models.ForeignKey('Place', models.CASCADE, related_name='to_place', related_query_name='to_place')
    distance = models.FloatField('Distance kilometers', default=1)

    def __str__(self):
        return f'{self.from_place.name} > {self.to_place.name} | {self.distance} km'


class SettlementPosition(models.Model):
    is_voting = models.BooleanField('Is voting position', default=False)
    title = models.CharField('Title', max_length=50, unique=True)
    name = models.CharField('Name', max_length=100)
    name_female = models.CharField('Name female', max_length=100, blank=True)
    description = models.TextField('Description', blank=True)
    character_filters = models.JSONField('Characters filters', default=dict, blank=True)
    points_mods = models.JSONField(
        verbose_name='Points from character attrs',
        help_text='Example: {"positive": {"max": ["magic", "fighting"], "exact": "energy"}} '
                  'Options: positive/negative, max/min/avg/exact.',
        default=dict,
        blank=True
    )
    value = models.PositiveSmallIntegerField(
        'Value of position', validators=[MinValueValidator(100), MaxValueValidator(1000)], default=500
    )
    min_number = models.PositiveSmallIntegerField(default=1)
    max_number = models.PositiveSmallIntegerField(blank=True, null=True)
    population_ratio = models.FloatField(
        verbose_name='Additional number depending on population',
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )

    def __str__(self):
        return self.title


char_fields = get_fields_data(Character)
place_fields = get_fields_data(Place)
plan_fields = get_fields_data(Plan)
settlement_fields = get_fields_data(Settlement)
position_fields = get_fields_data(SettlementPosition)
char_attrs_ranged = tuple(
    name for name, ranges in char_fields.items() if ranges['min'] == 100 and ranges['max'] == 1000
)
