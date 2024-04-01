from django.contrib import admin

from .models import HIT, Assignment, Worker


class HITAdmin(admin.ModelAdmin):
    list_display = ("id", "enabled", "created_at", "topic", "location")


class WorkerAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    readonly_fields = ("id",)


class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "hit", "worker", "stage")
    readonly_fields = ("id",)


admin.site.register(HIT, HITAdmin)
admin.site.register(Worker, WorkerAdmin)
admin.site.register(Assignment, AssignmentAdmin)
