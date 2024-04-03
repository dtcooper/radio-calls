import datetime

from django.contrib import admin, messages
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.utils.html import format_html

from admin_extra_buttons.api import ExtraButtonsMixin, button, confirm_action
from durationwidget.widgets import TimeDurationWidget

from .constants import CORE_ENGLISH_SPEAKING_COUNTRIES, CORE_ENGLISH_SPEAKING_COUNTRIES_NAMES
from .models import HIT, Assignment, Worker


class BaseModelAdmin(admin.ModelAdmin):
    list_max_show_all = 2500
    list_per_page = 200
    show_facets = admin.ShowFacets.ALWAYS
    save_on_top = True

    formfield_overrides = {models.DurationField: {"widget": TimeDurationWidget}}


def has_publish_permission(request, hit, **kwargs):
    return request.user.is_superuser and hit.status == HIT.Status.LOCAL


class HITAdmin(ExtraButtonsMixin, BaseModelAdmin):
    FIELDSET_HIT_SETTINGS = ("HIT Settings", {"fields": ("title", "description", "keywords", "duration")})
    FIELDSET_QUALIFICATIONS = (
        "Qualifications",
        {
            "fields": (
                "qualification_masters",
                "qualification_num_previously_approved",
                "qualification_approval_rate",
                "qualification_countries",
                "qualification_adult",
            )
        },
    )
    FIELDSET_ASSIGNMENT_SETTINGS = (
        "Assignment Settings",
        {"fields": ("assignment_number", "assignment_reward", "assignment_duration")},
    )
    add_fieldsets = (
        (None, {"fields": ("name", "topic", "show_host")}),
        FIELDSET_HIT_SETTINGS,
        FIELDSET_ASSIGNMENT_SETTINGS,
        FIELDSET_QUALIFICATIONS,
        (
            "Miscellaneous",
            {
                "classes": ("collapse",),
                "fields": (
                    "min_call_duration",
                    "leave_voicemail_after_duration",
                    "approval_delay",
                ),
            },
        ),
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "topic",
                    "show_host",
                    "cost_estimate",
                    "status",
                    "submitted_at",
                    "is_running",
                    "amazon_id",
                )
            },
        ),
        FIELDSET_HIT_SETTINGS,
        FIELDSET_ASSIGNMENT_SETTINGS,
        FIELDSET_QUALIFICATIONS,
        (
            "Miscellaneous",
            {
                "classes": ("collapse",),
                "fields": (
                    "min_call_duration",
                    "leave_voicemail_after_duration",
                    "created_at",
                    "created_by",
                    "approval_delay",
                    "unique_request_token",
                    "approval_code",
                    "publish_api_exception",
                ),
            },
        ),
    )
    list_display = ("name", "created_at", "topic", "status", "submitted_at", "is_running")
    readonly_fields = (
        "amazon_id",
        "approval_code",
        "created_at",
        "created_by",
        "cost_estimate",
        "is_running",
        "publish_api_exception",
        "status",
        "submitted_at",
        "unique_request_token",
    )
    submitted_readonly_fields = (
        "approval_delay",
        "assignment_duration",
        "assignment_number",
        "assignment_reward",
        "description",
        "duration",
        "keywords",
        "name",
        "qualification_adult",
        "qualification_approval_rate",
        "qualification_countries",
        "qualification_masters",
        "qualification_num_previously_approved",
        "title",
    )

    def get_fieldsets(self, request, obj: HIT = None):
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj: HIT = None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is not None and obj.status != HIT.Status.LOCAL:
            return readonly_fields + self.submitted_readonly_fields
        return readonly_fields

    @button(html_attrs={"style": "background-color: oklch(0.648 0.15 160); color: #000000"})
    def clone(self, request, pk):
        hit = get_object_or_404(HIT, pk=pk)
        new_hit = hit.clone()
        self.message_user(request, f"HIT {hit.name} was successfully cloned!")
        return redirect("admin:api_hit_change", object_id=new_hit.pk)

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
            description=f"HIT has an estimated cost of ${hit.cost_estimate()}.",
            message=format_html('Are you sure you want to publish HIT <em>"{}"</em> to Production?', hit.name),
            pk=pk,
            success_message=f"Published {hit.name} to Production! It should appear shortly.",
            error_message=f"An error occured while publishing {hit.name} to Production!",
            title="Publish HIT to Production",
        )

    def changeform_view(self, request, object_id, form_url, extra_context):
        if request.method != "POST":
            self.run_hit_warning_messages(request, self.model.objects.get(id=object_id))
        return super().changeform_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj: HIT, form, change):
        if not change:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)

    def run_hit_warning_messages(self, request, obj: HIT):
        # Run rudimentary warning checks
        def warn(msg):
            self.message_user(request, f"WARNING: {msg}", messages.WARNING)

        def name(field):
            return self.model._meta.get_field(field).verbose_name

        for check_duration_field in ("min_call_duration", "leave_voicemail_after_duration"):
            if getattr(obj, check_duration_field) > obj.assignment_duration:
                warn(f"{name(check_duration_field)} is longer than {name('assignment_duration')}")

        if obj.duration > datetime.timedelta(hours=2):
            warn(f"{name('duration')} is longer than two hours")

        if obj.assignment_duration > datetime.timedelta(minutes=45):
            warn(f"{name('assignment_duration')} is longer than 45 minutes")

        if obj.assignment_reward > 10:
            warn(f"{name('assignment_reward')} is more that $10")

        if obj.assignment_number > 150:
            warn(f"{name('assignment_number')} is more than 150")

        if not (datetime.timedelta(days=1) <= obj.approval_delay <= datetime.timedelta(days=3)):
            warn(f"{name('approval_delay')} should be between 1 and 3 days")

        if not obj.qualification_countries:
            warn(f"open to workers in ANY and ALL {name('qualification_countries')}")
        elif not CORE_ENGLISH_SPEAKING_COUNTRIES.issubset(set(c.code for c in obj.qualification_countries)):
            warn(
                f"{name('qualification_countries')} do not include workers from the 'core' English speaking countries:"
                f" {', '.join(CORE_ENGLISH_SPEAKING_COUNTRIES_NAMES)}"
            )


class WorkerAdmin(BaseModelAdmin):
    def has_add_permission(self, request):
        return False


class AssignmentAdmin(BaseModelAdmin):
    def has_add_permission(self, request):
        return False


admin.site.register(HIT, HITAdmin)
admin.site.register(Worker, WorkerAdmin)
admin.site.register(Assignment, AssignmentAdmin)
