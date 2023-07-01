from django import forms
from django.core.exceptions import ValidationError

from main.models import (
    Character,
    CharacterDataEffects,
    CharacterDataFilters,
    CharacterDataPlanFilters,
    Place,
    Plan,
    PlanFilters,
    Stage,
    PlanLock,
    PlanPause,
    PlanPlaceFilters,
    PlanSetFilters,
    SettlementPosition,
    char_fields,
    place_fields,
    plan_fields,
    settlement_fields
)
from main.utils import (
    check_characters_modifiers,
    check_json_keys,
    check_json_model_fields,
    check_modifiers,
    get_time_seconds
)


class CharacterForm(forms.ModelForm):
    model = Character

    def save(self, commit=True):
        if 'place' in self.changed_data:
            if self.initial.get('place'):
                place_previous = Place.objects.filter(id=self.initial['place']).first()
                place_previous.population -= 1
                place_previous.save()
            place_new = self.cleaned_data['place']
            if place_new:
                place_new.population += 1
                place_new.save()

        return super().save(commit=commit)


class CharacterDataEffectsForm(forms.ModelForm):
    model = CharacterDataEffects

    def clean(self):
        relationships_min = self.cleaned_data.get('relationships_min')
        relationships_max = self.cleaned_data.get('relationships_max')
        if relationships_min and relationships_max and relationships_min > relationships_max:
            raise ValidationError('relationships_min > relationships_max')
        return self.cleaned_data

    def clean_effects(self):
        return check_json_model_fields(self.cleaned_data['effects'], char_fields, is_validate=False)

    def clean_effects_max(self):
        return check_json_model_fields(self.cleaned_data['effects_max'], char_fields)

    def clean_effects_mods(self):
        return check_characters_modifiers(self.cleaned_data['effects_mods'], char_fields)

    def clean_effects_place_mods(self):
        return check_modifiers(self.cleaned_data['effects_place_mods'], place_fields)

    def clean_place_effects(self):
        return check_json_model_fields(self.cleaned_data['place_effects'], place_fields, is_validate=False)

    def clean_settlement_effects(self):
        return check_json_model_fields(self.cleaned_data['settlement_effects'], settlement_fields, is_validate=False)

    def clean_settlement_effects_max(self):
        return check_json_model_fields(
            self.cleaned_data['settlement_effects_max'], settlement_fields, is_validate=False
        )

    def clean_place_settlement_effects(self):
        return check_json_model_fields(
            self.cleaned_data['place_settlement_effects'], settlement_fields, is_validate=False
        )

    def clean_place_settlement_effects_max(self):
        return check_json_model_fields(
            self.cleaned_data['place_settlement_effects_max'], settlement_fields, is_validate=False
        )

    def clean_needs_mods(self):
        return check_json_keys(
            outer_data=self.cleaned_data['needs_mods'], valid_data={'energy', 'sleep', 'mood', 'health'}
        )


class PlanForm(forms.ModelForm):
    model = Plan


class PlanSetFiltersForm(forms.ModelForm):
    model = PlanSetFilters

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data['first_character'] and cleaned_data['second_character']:
            raise ValidationError('Specify one character data.')
        if not cleaned_data['first_character'] and not cleaned_data['second_character']:
            raise ValidationError('Specify one character data.')
        return cleaned_data


class StageForm(forms.ModelForm):
    model = Stage


class CharacterDataFiltersForm(forms.ModelForm):
    model = CharacterDataFilters

    def clean_filters(self):
        return check_json_model_fields(self.cleaned_data['filters'], char_fields, is_validate=False)

    def clean_points_mods(self):
        return check_json_model_fields(self.cleaned_data['points_mods'], char_fields, is_validate=False)


class CharacterDataPlanFiltersForm(forms.ModelForm):
    model = CharacterDataPlanFilters

    def clean_filters(self):
        return check_json_model_fields(self.cleaned_data['filters'], plan_fields, is_validate=False)


class PlanFiltersForm(forms.ModelForm):
    model = PlanFilters

    def save(self, commit=True):
        instance = super().save(commit=False)
        for k in ['time_from', 'time_to']:
            seconds_attr = f'{k}_seconds'
            if self.cleaned_data[k]:
                setattr(instance, seconds_attr, get_time_seconds(getattr(instance, k)))
            elif getattr(instance, seconds_attr):
                setattr(instance, seconds_attr, None)
        for k in ['time_min', 'time_max']:
            setattr(instance, f'{k}_seconds', get_time_seconds(getattr(instance, k)) if self.cleaned_data[k] else None)
        return super().save()


class PlanPlaceFiltersForm(forms.ModelForm):
    model = PlanPlaceFilters

    def clean_filters(self):
        data = self.cleaned_data['filters']
        check_json_model_fields(data, place_fields)
        return data

    def clean_attrs_importance(self):
        data = self.cleaned_data['attrs_importance']
        check_json_model_fields(data, place_fields, False, exclude=['random'])
        if data:
            total = sum([v for v in data.values()])
            if total != 1:
                raise ValidationError(f'Wrong sum of values: "{total}"')
        return data


class PlanLockForm(forms.ModelForm):
    model = PlanLock

    def check_filters(self, key):
        data = self.cleaned_data[key]
        if not data:
            return data
        return check_json_model_fields(data, place_fields)

    def clean_open_filters(self):
        return self.check_filters('open_filters')

    def clean_close_filters(self):
        return self.check_filters('close_filters')


class PlanPauseForm(forms.ModelForm):
    model = PlanPause

    @staticmethod
    def check(data):
        plan_titles = Plan.objects.values_list('title', flat=True)
        for title, pause in data.items():
            if title not in plan_titles:
                raise ValidationError('Plan not found: "{}"'.format(title))
            if not isinstance(pause, (float, int)):
                raise ValidationError('Wrong value: "{}"'.format(pause))
        return data

    def clean_first(self):
        return self.check(self.cleaned_data.get('first', {}))

    def clean_second(self):
        return self.check(self.cleaned_data.get('second', {}))


class PlaceForm(forms.ModelForm):
    model = Place

    def clean_lock_filters(self):
        return check_json_model_fields(self.cleaned_data['lock_filters'], char_fields)


class PlaceTransitionFormset(forms.BaseInlineFormSet):
    def save(self, commit=True):
        instances = super().save(commit=False)
        for instance in instances:
            instance.save()
            self.model.objects.update_or_create(
                from_place_id=instance.to_place_id,
                to_place_id=instance.from_place_id,
                defaults={'distance': instance.distance}
            )

        for obj in self.deleted_objects:
            obj.delete()
            self.model.objects.filter(from_place_id=obj.to_place_id, to_place_id=obj.from_place_id).delete()

        self.save_m2m()


class SettlementPositionForm(forms.ModelForm):
    model = SettlementPosition

    def clean_character_filters(self):
        data = self.cleaned_data['character_filters']
        check_json_model_fields(data, char_fields)
        return data
