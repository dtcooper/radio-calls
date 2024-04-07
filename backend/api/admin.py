import datetime
from urllib.parse import urlencode

from dateutil.parser import parse as dateutil_parse

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import F, Func, Value
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from admin_extra_buttons.api import ExtraButtonsMixin, button, confirm_action
from durationwidget.widgets import TimeDurationWidget

from .constants import CORE_ENGLISH_SPEAKING_COUNTRIES, CORE_ENGLISH_SPEAKING_COUNTRIES_NAMES, SIMULATED_PREFIX
from .models import HIT, Assignment, User, Worker
from .utils import short_datetime_str


class HITListDisplayMixin:
    @admin.display(description="HIT")
    def hit_display(self, obj):
        return format_html('<a href="{}">{}</a>', reverse("admin:api_hit_change", args=(obj.hit.id,)), obj.hit.name)


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
    list_filter = ("status", "submitted_at", "created_at")
    search_fields = ("amazon_id", "name")
    date_hierarchy = "submitted_at"

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if request.user.first_name:
            initial["show_host"] = request.user.first_name
        return initial

    @admin.display(description="is running?", boolean=True)
    def is_running(self, obj: HIT):
        if obj.submitted_at:
            return obj.submitted_at + obj.duration >= timezone.now()
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
        permission=lambda request, hit, **kw: settings.ALLOW_PUBLISH_TO_MTURK_PRODUCTION
        and request.user.has_perm("api.publish_production_hit")
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
            error_message=f"An error occured while publishing {hit.name} to production!",
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

        def name(field) -> str:
            return self.model._meta.get_field(field).verbose_name

        cost_estimate = obj.get_cost_estimate()
        if cost_estimate >= 250:
            warn(f"The cost estimate for this HIT is ${cost_estimate} and exceeds $250. Please verify this is correct!")

        for check_duration_field in ("min_call_duration", "leave_voicemail_after_duration"):
            if getattr(obj, check_duration_field) + datetime.timedelta(minutes=10) > obj.assignment_duration:
                warn(
                    f"{name(check_duration_field).capitalize()} is 10 minutes less than {name('assignment_duration')}!"
                    " This may not give workers enough time."
                )

        if not (datetime.timedelta(minutes=20) <= obj.duration <= datetime.timedelta(hours=2)):
            warn(f"{name('duration')} is not between 20 minutes and 2 hours. This may cause unexpected results.")

        if obj.assignment_duration > datetime.timedelta(minutes=45):
            warn(f"{name('assignment_duration').capitalize()} is longer than 45 minutes")

        if obj.assignment_reward > 10:
            warn(f"{name('assignment_reward').capitalize()} is more that $10")

        if obj.assignment_number > 150:
            warn(f"{name('assignment_number').capitalize()} is more than 150")

        if not (datetime.timedelta(days=1) <= obj.approval_delay <= datetime.timedelta(days=3)):
            warn(f"{name('approval_delay').capitalize()} should be between 1 and 3 days")

        if not obj.qualification_countries:
            warn(f"open to workers in ANY and ALL {name('qualification_countries')}")
        elif not CORE_ENGLISH_SPEAKING_COUNTRIES.issubset(set(c.code for c in obj.qualification_countries)):
            warn(
                f"{name('qualification_countries').capitalize()} do not include workers from the 'core' English"
                f" speaking countries: {', '.join(CORE_ENGLISH_SPEAKING_COUNTRIES_NAMES)}."
            )


class WorkerAndAssignmentBaseAdmin(BaseModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return (
            # Change "simulated" objects only, unless you're the superuser in debug mode
            request.user.has_perm(f"api.change_{self.model._meta.model_name}")
            and (obj is None or obj.amazon_id.startswith(SIMULATED_PREFIX))
        ) or (request.user.is_superuser and settings.DEBUG)


class AssignmentAdmin(ExtraButtonsMixin, HITListDisplayMixin, WorkerAndAssignmentBaseAdmin):
    fields = (
        "amazon_id",
        "hit",
        "worker",
        "progress_display",
        "call_step",
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
    list_display = (
        "amazon_id",
        "created_at",
        "call_step",
        "worker_display",
        "hit_display",
        "call_duration",
        "last_progress",
        "left_voicemail",
    )
    readonly_fields = (
        "amazon_id",
        "call_duration",
        "created_at",
        "get_amazon_status",
        "hit_display",
        "left_voicemail",
        "progress_display",
        "voicemail_duration",
        "voicemail_url",
        "last_progress",
        "worker_display",
    )
    list_filter = ("hit", "call_step")
    search_fields = ("amazon_id", "worker__name", "hit__name")

    @admin.display(description="Worker")
    def worker_display(self, obj):
        return format_html('<a href="{}">{}</a>', reverse("admin:api_worker_change", args=(obj.worker.id,)), obj.worker)

    @admin.display(boolean=True, ordering="voicemail_duration")
    def left_voicemail(self, obj: Assignment):
        return bool(obj.voicemail_url)

    def call_duration(self, obj: Assignment):
        if obj.call_completed_at is not None and obj.call_started_at is not None:
            return obj.call_completed_at - obj.call_started_at
        return None

    @admin.display(ordering=Func(F("progress"), Value(1), function="array_length"))
    def last_progress(self, obj: Assignment):
        if obj.progress:
            return f"{obj.progress[-1].split('/', 1)[1]} ({len(obj.progress)} total)"
        return "(0 total)"

    @admin.display(description="progress")
    def progress_display(self, obj: Assignment):
        try:
            splits = map(lambda s: s.split("/", 1), obj.progress)
            encoded = ((short_datetime_str(dateutil_parse(dt)), s) for dt, s in splits)
            return format_html("<ol>{}</ol>", format_html_join("\n", "<li>{} &mdash; {}</li>", encoded)) or None
        except Exception:
            return f"Error parsing progress: {obj.progress}"


class AssignmentInline(HITListDisplayMixin, admin.TabularInline):
    model = Assignment
    fields = ("amazon_id", "hit_display", "created_at", "call_step")
    readonly_fields = ("created_at", "hit_display")
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class WorkerAdmin(WorkerAndAssignmentBaseAdmin):
    fields = ("amazon_id", "name", "gender", "location", "ip_address", "created_at")
    readonly_fields = ("amazon_id", "created_at")
    list_display = ("amazon_id", "name", "gender", "location")
    search_fields = ("amazon_id", "name", "location")
    inlines = (AssignmentInline,)


admin.site.unregister(Group)
admin.site.register(User, UserAdmin)
admin.site.register(HIT, HITAdmin)
admin.site.register(Worker, WorkerAdmin)
admin.site.register(Assignment, AssignmentAdmin)
