import datetime
from urllib.parse import urlencode

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import Count, Exists, F, Func, OuterRef, Subquery, Value
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from admin_extra_buttons.api import ExtraButtonsMixin, button, confirm_action
from durationwidget.widgets import TimeDurationWidget

from .constants import CORE_ENGLISH_SPEAKING_COUNTRIES, CORE_ENGLISH_SPEAKING_COUNTRIES_NAMES, SIMULATED_PREFIX
from .models import HIT, Assignment, Caller, Topic, User, Voicemail, Worker, WorkerPageLoad
from .utils import block_or_unblock_workers, get_mturk_client, short_datetime_str


ATTR_COLORS = {
    "success": ("oklch(0.648 0.15 160)", "#000000"),
    "warning": ("oklch(0.8471 0.199 83.87)", "#000000"),
    "error": ("oklch(0.7176 0.221 22.18)", "#000000"),
    "info": ("oklch(0.7206 0.191 231.6)", "#000000"),
    "pink": ("oklch(0.6971 0.329 342.55)", "oklch(0.9871 0.0106 342.55)"),
}


def attr_color(color):
    bgcolor, fgcolor = ATTR_COLORS[color]
    return {"style": f"background-color: {bgcolor}; color: {fgcolor}"}


class UserAdmin(BaseUserAdmin):
    list_max_show_all = 2500
    list_per_page = 200
    show_facets = admin.ShowFacets.ALWAYS
    save_on_top = True
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


class HITListDisplayMixin:
    @admin.display(description="HIT")
    def hit_display(self, obj):
        return format_html('<a href="{}">{}</a>', reverse("admin:api_hit_change", args=(obj.hit.id,)), obj.hit.name)


class PrefetchRelatedMixin:
    prefetch_related = None

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if self.prefetch_related is not None:
            queryset = queryset.prefetch_related(*self.prefetch_related)
        return queryset


class NumAssignmentsMixin:
    def get_queryset(self, request):
        if self.model == Assignment:
            annotation = Subquery(
                Assignment.objects.filter(worker_id=OuterRef("worker_id"))
                .values("worker_id")
                .annotate(count=Count("*"))
                .values("count")[:1]
            )
        else:
            annotation = Count("assignment")
        return super().get_queryset(request).annotate(num_assignments=annotation)

    @admin.display(description="Worker assignment count", ordering="num_assignments")
    def num_assignments(self, obj):
        url = reverse("admin:api_assignment_changelist")
        if self.model == HIT:
            query = {"hit__id__exact": obj.id}
        else:
            query = {"worker__id__exact": obj.worker_id if self.model == Assignment else obj.id}
        return format_html('<a href="{}">{}</a>', f"{url}?{urlencode(query)}", obj.num_assignments)


class BaseModelAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    date_hierarchy = "created_at"
    list_max_show_all = 2500
    list_per_page = 200
    show_facets = admin.ShowFacets.ALWAYS
    save_on_top = True
    formfield_overrides = {
        models.DurationField: {"widget": TimeDurationWidget},
        models.CharField: {"widget": forms.TextInput(attrs={"style": "width: 75%"})},
    }


def has_publish_permission(request, hit, **kwargs):
    return request.user.is_superuser and hit.status == HIT.Status.LOCAL


class HITAdmin(NumAssignmentsMixin, BaseModelAdmin):
    change_form_template = "admin/api/hit/change_form.html"
    change_list_template = "admin/api/hit/change_list.html"

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
                    "get_unit_cost",
                    "status",
                    "submitted_at",
                    "get_amazon_status",
                    "is_running",
                    "num_assignments",
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
    list_display = (
        "name",
        "created_at",
        "topic",
        "status",
        "submitted_at",
        "is_running",
        "num_assignments",
        "assignment_reward",
        "get_unit_cost",
        "get_cost_estimate",
    )
    readonly_fields = (
        "amazon_id",
        "approval_code",
        "created_at",
        "created_by",
        "get_amazon_status",
        "get_cost_estimate",
        "get_unit_cost",
        "is_running",
        "num_assignments",
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

    def add_balance_to_context(self, extra_context=None):
        extra_context = extra_context or {}
        client = get_mturk_client(production=settings.ALLOW_MTURK_PRODUCTION_ACCESS)
        extra_context["balance"] = client.get_account_balance()["AvailableBalance"]
        return extra_context

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = self.add_balance_to_context(extra_context)
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def changelist_view(self, request, extra_context=None):
        extra_context = self.add_balance_to_context(extra_context)
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="Is running?", boolean=True)
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
        html_attrs=attr_color("success"),
        permission=lambda request, hit, **kw: request.user.has_perm("api.add_hit"),
    )
    def clone(self, request, pk):
        hit = get_object_or_404(HIT, pk=pk)
        new_hit = hit.clone()
        self.message_user(request, f"HIT {hit.name} was successfully cloned!")
        return redirect("admin:api_hit_change", object_id=new_hit.pk)

    @button(
        html_attrs=attr_color("warning"),
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
        html_attrs=attr_color("error"),
        permission=lambda request, hit, **kw: settings.ALLOW_MTURK_PRODUCTION_ACCESS
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

        unit_cost = obj.get_unit_cost()
        if unit_cost > 5:
            warn(f"The unit cost for this HIT is ${unit_cost} and exceeds $5. Please verify this is correct.")

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


class WorkerAndAssignmentBaseAdmin(NumAssignmentsMixin, BaseModelAdmin):
    actions = ("mark_good_workers", "unmark_good_workers", "block_workers", "unblock_workers")

    def has_block_permission(self, request):
        return request.user.has_perm("api.block_worker")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return (
            # Change "simulated" objects only, unless you're the superuser in debug mode
            request.user.has_perm(f"api.change_{self.model._meta.model_name}")
            and (obj is None or obj.amazon_id.startswith(SIMULATED_PREFIX))
        ) or (request.user.is_superuser and settings.DEBUG)

    @button(
        html_attrs=attr_color("info"),
        permission=lambda request, hit, **kw: request.user.has_perm("api.block_worker"),
        label="Resynchronize blocks",
    )
    def resync_blocks(self, request):
        Worker.resync_blocks()
        self.message_user(request, "Worker blocks have been resynchronized!")

    def _get_worker_queryset(self, queryset):
        if self.model == Assignment:
            queryset = Worker.objects.filter(assignment__id__in=list(queryset.values_list("id", flat=True)))
        return queryset

    @admin.action(description="Block selected worker(s)", permissions=("block",))
    def block_workers(self, request, queryset):
        queryset = self._get_worker_queryset(queryset)
        blocks = filter(None, (w.block() for w in queryset))
        num_blocks = len(list(blocks))
        self.message_user(request, f"Blocked {num_blocks} worker(s)", messages.WARNING)

    @admin.action(description="Unblock selected worker(s)", permissions=("block",))
    def unblock_workers(self, request, queryset):
        queryset = self._get_worker_queryset(queryset)
        unblocks = filter(None, (w.unblock() for w in queryset))
        num_unblocks = len(list(unblocks))
        self.message_user(request, f"Unblocked {num_unblocks} worker(s)", messages.WARNING)

    @admin.action(description="Mark as good worker(s)", permissions=("change",))
    def mark_good_workers(self, request, queryset):
        num_marked = self._get_worker_queryset(queryset).update(is_good_worker=True)
        self.message_user(request, f"{num_marked} worker(s) marked as good", messages.SUCCESS)

    @admin.action(description="Unmark as good worker(s)", permissions=("change",))
    def unmark_good_workers(self, request, queryset):
        num_unmarked = self._get_worker_queryset(queryset).update(is_good_worker=False)
        self.message_user(request, f"{num_unmarked} worker(s) unmarked as good", messages.WARNING)


class AssignmentAdmin(HITListDisplayMixin, PrefetchRelatedMixin, WorkerAndAssignmentBaseAdmin):
    fields = (
        "amazon_id",
        "hit",
        "worker",
        "is_good_worker",
        "worker_blocked",
        "progress_display",
        "created_at",
        "call_step",
        "call_started_at",
        "call_connected_at",
        "call_completed_at",
        "get_call_duration",
        "num_assignments",
        "words_to_pronounce",
        "left_voicemail",
        "voicemail_duration",
        "voicemail_url_display",
        "feedback",
        "get_amazon_status",
        "user_agent",
    )
    list_display = (
        "amazon_id",
        "created_at",
        "call_step",
        "worker_display",
        "hit_display",
        "left_voicemail",
        "get_call_duration",
        "last_progress",
        "num_assignments",
        "is_good_worker",
        "worker_blocked",
    )
    readonly_fields = (
        "amazon_id",
        "created_at",
        "get_amazon_status",
        "get_call_duration",
        "hit_display",
        "is_good_worker",
        "last_progress",
        "left_voicemail",
        "num_assignments",
        "progress_display",
        "user_agent",
        "voicemail_duration",
        "voicemail_url_display",
        "worker_blocked",
        "worker_display",
    )
    list_filter = ("hit", "call_step", "worker__blocked", "worker__is_good_worker")
    search_fields = ("amazon_id", "worker__name", "hit__name", "worker__amazon_id", "hit__amazon_id")
    prefetch_related = ("hit", "worker")

    @admin.display(description="Good worker", boolean=True, ordering="worker__is_good_worker")
    def is_good_worker(self, obj: Assignment):
        return obj.worker.is_good_worker

    @admin.display(description="Worker")
    def worker_display(self, obj: Assignment):
        return format_html('<a href="{}">{}</a>', reverse("admin:api_worker_change", args=(obj.worker.id,)), obj.worker)

    @admin.display(description="Blocked", boolean=True, ordering="worker__blocked")
    def worker_blocked(self, obj: Assignment):
        return obj.worker.blocked

    @admin.display(description="Voicemail")
    def voicemail_url_display(self, obj: Assignment):
        if obj.voicemail_url:
            return format_html('<a href="{}">{}</a>', obj.voicemail_url, obj.voicemail_url)

    @admin.display(boolean=True, ordering="voicemail_duration")
    def left_voicemail(self, obj: Assignment):
        return bool(obj.voicemail_url)

    @admin.display(ordering=Func(F("progress"), Value(1), function="array_length"))
    def last_progress(self, obj: Assignment):
        if obj.progress:
            date, progress = obj.progress[-1].split("/", 1)
            return format_html("{}<br>{}<br>{}", short_datetime_str(date), progress, f"({len(obj.progress)} total)")
        return "0 total"

    @admin.display(description="progress")
    def progress_display(self, obj: Assignment):
        try:
            splits = map(lambda s: s.split("/", 1), obj.progress)
            encoded = ((short_datetime_str(date), progress) for date, progress in splits)
            return format_html("<ol>{}</ol>", format_html_join("\n", "<li>{} &mdash; {}</li>", encoded)) or None
        except Exception:
            return f"Error parsing progress: {obj.progress}"


class AssignmentInline(HITListDisplayMixin, PrefetchRelatedMixin, admin.TabularInline):
    model = Assignment
    fields = ("amazon_id", "hit_display", "created_at", "call_step")
    readonly_fields = ("created_at", "hit_display")
    show_change_link = True
    prefetch_related = ("hit", "worker")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class WorkerAdmin(WorkerAndAssignmentBaseAdmin):
    fields = (
        "amazon_id",
        "is_good_worker",
        "created_at",
        "name",
        "gender",
        "num_assignments",
        "location",
        "ip_address",
        "blocked",
    )
    readonly_fields = ("amazon_id", "blocked", "created_at", "num_assignments", "worker_display")
    editable_fields = ("is_good_worker",)  # Only fields we're allowed to edit
    list_display = (
        "amazon_id",
        "is_good_worker",
        "created_at",
        "worker_display",
        "location",
        "num_assignments",
        "blocked",
    )
    search_fields = ("amazon_id", "name", "location")
    list_filter = ("assignment__hit", "gender", "blocked", "is_good_worker")
    inlines = (AssignmentInline,)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if False or settings.DEBUG:
            return readonly_fields
        else:
            # Mark all fields EXCEPT editable fields as readonly when not debugging
            return (set(readonly_fields) | {f.name for f in self.model._meta.get_fields()}) - set(self.editable_fields)

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("api.change_worker")

    def worker_display(self, obj: Worker):
        return str(obj)

    @button(
        html_attrs=attr_color("error"),
        permission=lambda request, hit, **kw: request.user.has_perm("api.block_worker"),
        label="Block",
    )
    def block_worker(self, request, pk):
        worker = get_object_or_404(Worker, pk=pk)
        success = worker.block()
        if success:
            self.message_user(request, f"Worker {worker.name} was successfully blocked!", messages.WARNING)
        else:
            self.message_user(request, f"Could not block {worker.name} (API error or simulated user)", messages.ERROR)
        return redirect("admin:api_worker_change", object_id=worker.pk)

    @button(
        html_attrs=attr_color("success"),
        permission=lambda request, hit, **kw: request.user.has_perm("api.block_worker"),
        label="Unblock",
    )
    def unblock_worker(self, request, pk):
        worker = get_object_or_404(Worker, pk=pk)
        success = worker.unblock()
        if success:
            self.message_user(request, f"Worker {worker.name} was successfully unblocked!", messages.WARNING)
        else:
            self.message_user(request, f"Could not unblock {worker.name} (API error or simulated user)", messages.ERROR)
        return redirect("admin:api_worker_change", object_id=worker.pk)


class HasAssociatedWorkerListFilter(admin.SimpleListFilter):
    title = "has associated worker"
    parameter_name = "has_associated"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            queryset = queryset.filter(worker_id__isnull=False)
        elif value == "no":
            queryset = queryset.filter(worker_id__isnull=True)
        return queryset


class IsGoodWorkerListFilter(admin.SimpleListFilter):
    title = "good worker"
    parameter_name = "is_good_worker"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            queryset = queryset.filter(is_good_worker=True)
        elif value == "no":
            queryset = queryset.filter(is_good_worker=False)
        return queryset


class WorkerPageLoadAdmin(BaseModelAdmin):
    fields = list_display = readonly_fields = (
        "created_at",
        "worker_display",
        "had_amp_encoded",
        "assignment_display",
        "hit_display",
        "has_associated_worker",
        "is_good_worker",
        "blocked",
    )
    list_filter = ("had_amp_encoded", HasAssociatedWorkerListFilter, IsGoodWorkerListFilter)
    actions = ("block_workers", "unblock_workers")

    @admin.action(description="Block selected worker(s)", permissions=("block",))
    def block_workers(self, request, queryset):
        queryset = queryset.filter(is_good_worker=False).values_list("worker_amazon_id", flat=True)
        blocks = filter(None, block_or_unblock_workers(queryset, block=True))
        num_blocks = len(list(blocks))
        self.message_user(request, f"Blocked {num_blocks} worker(s)", messages.WARNING)

    @admin.action(description="Unblock selected worker(s)", permissions=("block",))
    def unblock_workers(self, request, queryset):
        queryset = queryset.values_list("worker_amazon_id", flat=True)
        unblocks = filter(None, block_or_unblock_workers(queryset, block=False))
        num_unblocks = len(list(unblocks))
        self.message_user(request, f"Unblocked {num_unblocks} worker(s)", messages.WARNING)

    def _display_helper(self, obj: WorkerPageLoad, field):
        id_value = getattr(obj, f"{field}_id")
        amazon_id = getattr(obj, f"{field}_amazon_id")
        if id_value:
            return format_html("<a href={}>{}</a>", reverse(f"admin:api_{field}_change", args=(id_value,)), amazon_id)
        else:
            return amazon_id

    @admin.display(description="Good worker", boolean=True, ordering="is_good_worker")
    def is_good_worker(self, obj: WorkerPageLoad):
        return obj.is_good_worker

    @admin.display(description="Worker", ordering="worker_amazon_id")
    def worker_display(self, obj: WorkerPageLoad):
        return self._display_helper(obj, "worker")

    @admin.display(description="Assignment", ordering="assignment_amazon_id")
    def assignment_display(self, obj: WorkerPageLoad):
        return self._display_helper(obj, "assignment")

    @admin.display(description="HIT", ordering="hit_amazon_id")
    def hit_display(self, obj: WorkerPageLoad):
        return self._display_helper(obj, "hit")

    @admin.display(boolean=True)
    def has_associated_worker(self, obj: WorkerPageLoad):
        return obj.worker_id is not None

    @admin.display(boolean=True)
    def blocked(self, obj: WorkerPageLoad):
        return obj.blocked

    def get_queryset(self, request):
        associated_worker_subquery = Worker.objects.filter(amazon_id=OuterRef("worker_amazon_id"))
        return (
            super()
            .get_queryset(request)
            .annotate(
                is_good_worker=Exists(associated_worker_subquery.filter(is_good_worker=True)),
                blocked=Exists(associated_worker_subquery.filter(blocked=True)),
                **{
                    f"{m._meta.model_name}_id": m.objects.filter(
                        amazon_id=OuterRef(f"{m._meta.model_name}_amazon_id")
                    ).values("id")[:1]
                    for m in (Worker, Assignment, HIT)
                },
            )
        )

    def has_block_permission(self, request):
        return request.user.has_perm("api.block_worker")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request

    def has_change_permission(self, request, obj=None):
        return False


PLAYER_HTML = '<audio controls src="{}" style="height: 28px" />'
LIST_BTN_HTML = '<a type="button" class="button" style="padding: 5px 7px; margin: 0" href="{}">{}</a>'


class TopicAdmin(BaseModelAdmin):
    change_form_template = "admin/api/topic/change_form.html"
    change_list_template = "admin/api/topic/change_list.html"
    list_display = ("name", "is_active", "recording_player", "created_at", "created_by", "mark_active_btn")
    fields = ("name", "is_active", "recording", "recording_player", "created_by", "created_at")
    readonly_fields = ("recording_player", "mark_active_btn", "created_by", "created_at")

    def save_model(self, request, obj: HIT, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @button(
        html_attrs=attr_color("info"),
        label="Mark active",
        permission=lambda request, topic, **kw: request.user.has_perm("api.change_topic"),
    )
    def mark_active(self, request, pk):
        topic = Topic.objects.get(id=pk)
        topic.is_active = True
        topic.save()
        self.message_user(request, f'Marked topic "{topic.name}" active!"')
        return redirect("admin:api_topic_changelist")

    @admin.display(description="Activate")
    def mark_active_btn(self, obj):
        return format_html(LIST_BTN_HTML, reverse("admin:api_topic_mark_active", args=(obj.id,)), "Mark active")

    @admin.display(description="Player")
    def recording_player(self, obj):
        return format_html(PLAYER_HTML, obj.recording.url)

    @staticmethod
    def topic_extra_context():
        return {"active_topic": Topic.get_active()}

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = self.topic_extra_context()
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def changelist_view(self, request, extra_context=None):
        extra_context = self.topic_extra_context()
        return super().changelist_view(request, extra_context=extra_context)


class CallerAdmin(BaseModelAdmin):
    list_display = ("number", "name_display", "wants_calls", "location", "created_at", "call_now_btn")
    fields = ("name", "number", "wants_calls", "location", "created_at")
    readonly_fields = ("name_display", "created_at", "call_now_btn")
    ordering = ("name",)

    @admin.display(description="Name", ordering="name")
    def name_display(self, obj):
        return obj.name or mark_safe("<em>Unnamed</em>")

    @button(
        html_attrs=attr_color("info"),
        label="Call now!",
        permission=lambda request, caller, **kw: request.user.has_perm("api.change_caller") and caller.wants_calls,
    )
    def call_now(self, request, pk):
        caller = Caller.objects.get(id=pk)
        self.message_user(request, f'Calling "{caller}" now!', level=messages.WARNING)
        return redirect("admin:api_caller_changelist")

    @admin.display(description="Call")
    def call_now_btn(self, obj):
        if obj.wants_calls:
            return format_html(LIST_BTN_HTML, reverse("admin:api_caller_call_now", args=(obj.id,)), "Call now!")
        else:
            return mark_safe("<em>Doesn't want calls</em>")


class VoicemailAdmin(BaseModelAdmin):
    list_display = ("caller_display", "url_player", "duration", "created_at")
    fields = ("caller_display", "url_player", "url_link", "duration", "created_at")
    readonly_fields = ("caller_display", "url_link", "url_player", "duration", "created_at")

    @admin.display(description="Player")
    def url_player(self, obj):
        return format_html(PLAYER_HTML, obj.url)

    @admin.display(description="URL link")
    def url_link(self, obj):
        return format_html('<a href="{}" target="_blank">External link</a>', obj.url)

    @admin.display(description="Caller", ordering="caller")
    def caller_display(self, obj):
        return obj.caller or mark_safe("<em>Unknown caller</em>")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.unregister(Group)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(Caller, CallerAdmin)
admin.site.register(HIT, HITAdmin)
admin.site.register(Topic, TopicAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Worker, WorkerAdmin)
admin.site.register(WorkerPageLoad, WorkerPageLoadAdmin)
admin.site.register(Voicemail, VoicemailAdmin)
