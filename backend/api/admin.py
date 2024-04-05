import datetime
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.html import format_html

from admin_extra_buttons.api import ExtraButtonsMixin, button, confirm_action
from durationwidget.widgets import TimeDurationWidget

from .constants import CORE_ENGLISH_SPEAKING_COUNTRIES, CORE_ENGLISH_SPEAKING_COUNTRIES_NAMES
from .models import HIT, Assignment, User, Worker


class BaseModelAdmin(admin.ModelAdmin):
    list_max_show_all = 2500
    list_per_page = 200
    show_facets = admin.ShowFacets.ALWAYS
    save_on_top = True

    formfield_overrides = {models.DurationField: {"widget": TimeDurationWidget}}


class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_superuser",
                    "groups",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    filter_horizontal = ("groups",)
    list_display = ("username", "email", "first_name", "last_name")
    list_filter = ("is_superuser", "is_active", "groups")

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser


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
                    "get_cost_estimate",
                    "status",
                    "submitted_at",
                    "get_amazon_status",
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
        "get_cost_estimate",
        "get_amazon_status",
        "is_running",
        "publish_api_exception",
        "status",
        "submitted_at",
        "unique_request_token",
    )
    submitted_additional_readonly_fields = (
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

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if request.user.first_name:
            initial["show_host"] = request.user.first_name
        return initial

    @admin.display(description="is running?", boolean=True)
    def is_running(self, obj: HIT):
        if obj.submitted_at:
            return obj.submitted_at + obj.duration + obj.assignment_duration >= timezone.now()
        return False

    def get_fieldsets(self, request, obj: HIT = None):
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj: HIT = None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is not None and obj.status != HIT.Status.LOCAL:
            return readonly_fields + self.submitted_additional_readonly_fields
        return readonly_fields

    @button(permission=lambda request, hit, **kw: request.user.has_perm("api.preview_hit"))
    def preview(self, request, pk):
        hit = get_object_or_404(HIT, pk=pk)
        return HttpResponseRedirect(f"/hit/?{urlencode({'dbId': hit.id})}")

    @button(
        html_attrs={"style": "background-color: oklch(0.648 0.15 160); color: #000000"},
        permission=lambda request, hit, **kw: request.user.has_perm("api.add_hit"),
    )
    def clone(self, request, pk):
        hit = get_object_or_404(HIT, pk=pk)
        new_hit = hit.clone()
        self.message_user(request, f"HIT {hit.name} was successfully cloned!")
        return redirect("admin:api_hit_change", object_id=new_hit.pk)

    @button(
        html_attrs={"style": "background-color: oklch(0.8471 0.199 83.87); color: #000000"},
        permission=lambda request, hit, **kw: request.user.has_perm("api.publish_sandbox_hit")
        and hit.status == HIT.Status.LOCAL,
    )
    def publish_to_sandbox(self, request, pk):
        hit = get_object_or_404(HIT, pk=pk)
        if hit.publish_to_mturk(production=False):
            self.message_user(request, f"Published {hit.name} to the Sandbox! It should appear shortly.")
        else:
            self.message_user(request, f"An error occured while publishing {hit.name} to the Sandbox!", messages.ERROR)

    @button(
        html_attrs={"style": "background-color: oklch(0.7176 0.221 22.18); color: #000000"},
        permission=lambda request, hit, **kw: request.user.has_perm("api.publish_production_hit")
        and hit.status == HIT.Status.LOCAL,
    )
    def publish_to_production(self, request, pk):
        hit = get_object_or_404(HIT, pk=pk)

        def publish_to_production(request):
            hit.publish_to_mturk(production=True)
            return redirect("admin:api_hit_change", object_id=hit.pk)

        return confirm_action(
            self,
            request,
            publish_to_production,
            description=f"HIT has an estimated cost of ${hit.get_cost_estimate()}.",
            message=format_html('Are you sure you want to publish HIT <em>"{}"</em> to Production?', hit.name),
            pk=pk,
            success_message=f"Published {hit.name} to Production! It should appear shortly.",
            error_message=f"An error occured while publishing {hit.name} to Production!",
            title="Publish HIT to Production",
        )

    def changeform_view(self, request, object_id, form_url, extra_context):
        if object_id is not None and request.method != "POST":
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

        cost_estimate = obj.get_cost_estimate()
        if cost_estimate >= 250:
            warn(f"The cost estimate for this HIT is ${cost_estimate} and exceeds $250. Please verify this is correct!")

        for check_duration_field in ("min_call_duration", "leave_voicemail_after_duration"):
            if getattr(obj, check_duration_field) + datetime.timedelta(minutes=15) > obj.assignment_duration:
                warn(
                    f"{name(check_duration_field)} is 15 minutes less than {name('assignment_duration')}! This may not"
                    " give workers enough time."
                )

        if obj.assignment_duration + datetime.timedelta(minutes=20) > obj.duration:
            warn(
                f"{name('assignment_duration')} is 20 minutes less than {name('duration')}! This may not give workers"
                " enough time."
            )

        if not (datetime.timedelta(minutes=20) <= obj.duration <= datetime.timedelta(hours=2)):
            warn(f"{name('duration')} is not between 20 minutes and 2 hours. This may cause unexpected results.")

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


class WorkerAndAssignmentBaseAdmin(BaseModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and settings.DEBUG


class WorkerAdmin(WorkerAndAssignmentBaseAdmin):
    pass


class AssignmentAdmin(ExtraButtonsMixin, WorkerAndAssignmentBaseAdmin):
    fields = (
        "amazon_id",
        "hit",
        "worker",
        "stage",
        "call_started_at",
        "call_completed_at",
        "words_to_pronounce",
        "voicemail_duration",
        "voicemail_url",
        "created_at",
        "left_voicemail",
        "call_duration",
        "get_amazon_status",
    )
    list_display = ("amazon_id", "stage", "worker", "hit", "call_duration", "left_voicemail")
    readonly_fields = (
        "amazon_id",
        "created_at",
        "voicemail_url",
        "call_duration",
        "voicemail_duration",
        "left_voicemail",
        "get_amazon_status",
    )

    @admin.display(boolean=True)
    def left_voicemail(self, obj: Assignment):
        return bool(obj.voicemail_url)

    def call_duration(self, obj: Assignment):
        if obj.call_completed_at is not None and obj.call_started_at is not None:
            return obj.call_completed_at - obj.call_started_at
        return None


admin.site.unregister(Group)
admin.site.register(User, UserAdmin)
admin.site.register(HIT, HITAdmin)
admin.site.register(Worker, WorkerAdmin)
admin.site.register(Assignment, AssignmentAdmin)
