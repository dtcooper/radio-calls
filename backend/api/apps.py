from django.apps import AppConfig, apps
from django.db.models import signals


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    verbose_name = "Mechanical Turk"

    def ready(self):
        signals.post_migrate.connect(self.create_groups, sender=self)

    def create_groups(self, using=None, *args, **kwargs):
        Group = apps.get_model("auth.Group")
        Permission = apps.get_model("auth.Permission")
        ContentType = apps.get_model("contenttypes.ContentType")
        content_types = [ContentType.objects.get_for_model(m) for m in apps.get_app_config("api").get_models()]
        permission_qs = Permission.objects.filter(content_type__in=content_types)

        additional_permissions = apps.get_model("api.HIT")._meta.permissions
        no_additional_permission_qs = permission_qs.exclude(codename__in=[p[0] for p in additional_permissions])

        all_groups = []
        group, _ = Group.objects.get_or_create(name="Edit assignments, HITs and workers (admin)")
        group.permissions.clear()
        group.permissions.add(*no_additional_permission_qs)
        all_groups.append(group)

        group, _ = Group.objects.get_or_create(name="View assignments, HITs and workers (admin)")
        group.permissions.clear()
        group.permissions.add(*no_additional_permission_qs.filter(codename__startswith="view"))
        all_groups.append(group)

        # Create one group per additional permission
        for permission_codename, permission_name in additional_permissions:
            group, _ = Group.objects.get_or_create(name=permission_name)
            group.permissions.clear()
            group.permissions.add(*permission_qs.filter(codename=permission_codename))
            all_groups.append(group)

        # Clean up groups that shouldn't exist
        Group.objects.exclude(id__in=[group.id for group in all_groups]).delete()
