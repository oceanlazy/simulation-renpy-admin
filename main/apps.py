from django.apps import AppConfig


class MainConfig(AppConfig):
    app_label = 'main'
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        import main.signals  # noqa
