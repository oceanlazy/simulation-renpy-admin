from django.apps import apps
from django.core.cache import cache
from django.db.models.signals import post_save
from main.models import Stage


def clear_cache_post_save(**_):
    cache.clear()
    for stage in Stage.objects.all():
        str(stage)


for model in apps.all_models['main'].values():
    post_save.connect(clear_cache_post_save, sender=model)
