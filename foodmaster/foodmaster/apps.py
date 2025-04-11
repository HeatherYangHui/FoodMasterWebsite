from django.apps import AppConfig


class FoodmasterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "foodmaster"

    def ready(self):
        # Import signals so they get registered
        import foodmaster.signals