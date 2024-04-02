from django.contrib import admin, messages
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.utils.html import format_html

from admin_extra_buttons.api import ExtraButtonsMixin, button, confirm_action
from durationwidget.widgets import TimeDurationWidget

from .models import HIT, Assignment, Worker


class BaseModelAdmin(admin.ModelAdmin):
    add_fields = None
    list_max_show_all = 2500
    list_per_page = 200
    show_facets = admin.ShowFacets.ALWAYS
    save_on_top = True
    save_as = True

    formfield_overrides = {models.DurationField: {"widget": TimeDurationWidget}}

    def get_fields(self, request, obj=None):
        if obj is None and self.add_fields is not None:
            return self.add_fields
        return super().get_fields(request, obj)


def has_publish_permission(request, hit, **kwargs):
    return request.user.is_superuser and hit.status == HIT.Status.LOCAL


class HITAdmin(ExtraButtonsMixin, BaseModelAdmin):
    readonly_fields = ("amazon_id", "created_by")

    # Call get_changeform_initial_data with latest values (Production only) if available

    @button(
        html_attrs={"style": "background-color: oklch(0.8471 0.199 83.87); color: #000000"},
        permission=has_publish_permission,
    )
    def publish_to_sandbox(self, request, pk):
        hit = get_object_or_404(HIT, pk=pk)
        if hit.publish_to_mturk(production=False):
            self.message_user(request, f"Published {hit.name} to the Sandbox! It should appear shortly.")
        else:
            self.message_user(request, f"An error occured while publishing {hit.name} to the Sandbox!", messages.ERROR)

    @button(
        html_attrs={"style": "background-color: oklch(0.7176 0.221 22.18); color: #000000"},
        permission=has_publish_permission,
    )
    def publish_to_production(self, request, pk):
        hit = get_object_or_404(HIT, pk=pk)

        def publish_to_production(request):
            hit.publish_to_mturk(production=False)
            return redirect("admin:api_hit_change", object_id=hit.pk)

        return confirm_action(
            self,
            request,
            publish_to_production,
            description="TODO COST SUMMARY GOES HERE",
            message=format_html('Are you sure you want to publish HIT <em>"{}"</em> to Production?', hit.name),
            pk=pk,
            success_message=f"Published {hit.name} to Production! It should appear shortly.",
            error_message=f"An error occured while publishing {hit.name} to Production!",
            title="Publish HIT to Production",
        )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class WorkerAdmin(BaseModelAdmin):
    def has_add_permission(self, request):
        return False


class AssignmentAdmin(BaseModelAdmin):
    def has_add_permission(self, request):
        return False


admin.site.register(HIT, HITAdmin)
admin.site.register(Worker, WorkerAdmin)
admin.site.register(Assignment, AssignmentAdmin)
