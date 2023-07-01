import datetime

from django.apps import apps
from django.contrib import admin
from django.contrib.auth.models import User
from main.forms import (
    CharacterForm,
    CharacterDataEffectsForm,
    CharacterDataFiltersForm,
    CharacterDataPlanFiltersForm,
    PlaceForm,
    PlaceTransitionFormset,
    PlanForm,
    PlanFiltersForm,
    StageForm,
    PlanLockForm,
    PlanPauseForm,
    PlanPlaceFiltersForm,
    PlanSetFiltersForm,
    SettlementPositionForm
)
from main.models import (
    Character,
    CharacterDataEffects,
    CharacterDataFilters,
    CharacterDataPlanFilters,
    CharacterRelationship,
    EventLog,
    Faction,
    FactionRelationship,
    Place,
    PlaceTransition,
    Plan,
    PlanData,
    PlanEffects,
    PlanEffectsSet,
    PlanFilters,
    PlanSetFilters,
    Stage,
    PlanLock,
    PlanPause,
    PlanPlaceFilters,
    Route,
    Settlement,
    SettlementPosition
)

user = User.objects.first()
admin.site.has_permission = lambda r: setattr(r, 'user', user) or True

for app_config in apps.get_app_configs():
    for model in app_config.get_models():
        if admin.site.is_registered(model):
            admin.site.unregister(model)


@admin.register(CharacterDataEffects)
class CharacterDataEffectsAdmin(admin.ModelAdmin):
    form = CharacterDataEffectsForm
    ordering = ['id']

    def has_module_permission(self, request):
        return False


@admin.register(CharacterDataFilters)
class CharacterDataFiltersAdmin(admin.ModelAdmin):
    form = CharacterDataFiltersForm
    ordering = ['title']

    def has_module_permission(self, request):
        return False


@admin.register(CharacterDataPlanFilters)
class CharacterDataPlanFiltersAdmin(admin.ModelAdmin):
    form = CharacterDataPlanFiltersForm
    ordering = ['title']

    def has_module_permission(self, request):
        return False


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    form = PlanForm

    list_display = ['title', 'min_points', 'id', 'is_char_available', 'is_player_available']
    ordering = ['-is_char_available', '-min_points', 'is_encounter']

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(id__in=[1, 2])  # used by game

    @staticmethod
    def delete_plan(pk):
        char_filters_update = []
        for char_filter_instance in CharacterDataPlanFilters.objects.all():
            filters = char_filter_instance.filters
            is_update = False
            if filters.get('id') == pk:
                del filters['id']
                is_update = True
            if pk in filters.get('id__in', []):
                filters['id__in'].remove(pk)
                is_update = True
            if is_update:
                char_filter_instance.filters = filters
                char_filters_update.append(char_filter_instance)
        if char_filters_update:
            CharacterDataPlanFilters.objects.bulk_update(char_filters_update, ['filters'])

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            self.delete_plan(obj.id)
        queryset.delete()

    def delete_model(self, request, obj):
        self.delete_plan(obj.id)
        super().delete_model(request, obj)


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    ordering = ['first_character_id', 'timestamp']
    list_display = ['get_time', 'first_character', 'second_character', 'get_plan_title', 'is_important']

    @admin.display(description='time')
    def get_time(self, obj):
        return datetime.timedelta(seconds=obj.timestamp)

    @admin.display(description='plan')
    def get_plan_title(self, obj):
        return obj.plan.title


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    form = StageForm
    ordering = ['-effects_id', '-filters_place_id', '-lock_id', '-plan_pause']

    def has_module_permission(self, request):
        return False


@admin.register(PlanEffects)
class PlanEffectsAdmin(admin.ModelAdmin):
    ordering = ['id']

    def has_module_permission(self, request):
        return False


@admin.register(PlanEffectsSet)
class PlanEffectsSetAdmin(admin.ModelAdmin):
    ordering = ['title']

    def has_module_permission(self, request):
        return False


@admin.register(PlanFilters)
class PlanFiltersAdmin(admin.ModelAdmin):
    form = PlanFiltersForm
    ordering = ['id']

    def has_module_permission(self, request):
        return False


@admin.register(PlanSetFilters)
class PlanSetFiltersAdmin(admin.ModelAdmin):
    form = PlanSetFiltersForm
    ordering = ['id']

    def has_module_permission(self, request):
        return False


@admin.register(PlanPlaceFilters)
class PlanPlaceFilterAdmin(admin.ModelAdmin):
    form = PlanPlaceFiltersForm
    ordering = ['title']

    def has_module_permission(self, request):
        return False


@admin.register(PlanLock)
class PlanLockAdmin(admin.ModelAdmin):
    form = PlanLockForm
    ordering = ['id']

    def has_module_permission(self, request):
        return False


@admin.register(PlanPause)
class PlanPauseAdmin(admin.ModelAdmin):
    form = PlanPauseForm
    ordering = ['id']

    def has_module_permission(self, request):
        return False


@admin.register(PlanData)
class PlanDataAdmin(admin.ModelAdmin):
    list_display = ['first_character', 'second_character']

    def save_model(self, request, obj, form, change):
        obj.save()
        Character.objects.filter(
            id__in=[obj.first_character_id, obj.second_character_id]
        ).update(
            plan_data=obj
        )


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return False


class CharacterRelationshipInline(admin.TabularInline):
    model = CharacterRelationship
    extra = 1
    fk_name = 'from_character'


class CharacterPlaceInline(admin.TabularInline):
    model = Place
    extra = 1
    fk_name = 'owner'


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'faction', 'place']
    ordering = ['first_name']
    inlines = [CharacterPlaceInline, CharacterRelationshipInline]
    form = CharacterForm

    def delete_model(self, request, obj):
        if obj.place:
            obj.place.population -= 1
            obj.place.save()
        return super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        places = set()
        for obj in queryset:
            if obj.place:
                obj.place.population -= 1
                places.add(obj.place)
        Place.objects.bulk_update(places, ['population'])
        return super().delete_queryset(request, queryset)


@admin.register(CharacterRelationship)
class CharacterRelationshipAdmin(admin.ModelAdmin):
    list_display = ['from_character', 'to_character', 'value']


class FactionRelationshipInline(admin.TabularInline):
    model = FactionRelationship
    extra = 1
    fk_name = 'from_faction'


@admin.register(Faction)
class FactionAdmin(admin.ModelAdmin):
    list_display = ['name']
    inlines = [FactionRelationshipInline]


@admin.register(FactionRelationship)
class FactionRelationshipAdmin(admin.ModelAdmin):
    list_display = ['from_faction', 'to_faction', 'value']


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    ordering = ['title']
    list_display = ['title', 'gold']


@admin.register(SettlementPosition)
class SettlementPositionAdmin(admin.ModelAdmin):
    list_display = ['name', 'population_ratio', 'is_voting', 'value']
    ordering = ['-value']
    form = SettlementPositionForm


class PlaceTransitionInline(admin.TabularInline):
    model = PlaceTransition
    formset = PlaceTransitionFormset
    extra = 1
    fk_name = 'from_place'


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    ordering = ['id']
    list_display = ['name', 'title', 'is_locked', 'beauty', 'safety', 'fertility']
    inlines = [PlaceTransitionInline]
    form = PlaceForm
