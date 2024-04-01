from django.contrib import admin

from .models import HIT, Assignment, Worker


class HITAdmin(admin.ModelAdmin):
    list_display = fields = ("name", "id", "topic", "created_at", "enabled", "location")
    readonly_fields = ("created_at",)


class WorkerAdmin(admin.ModelAdmin):
    list_display = fields = ("id", "created_at", "name", "gender")
    readonly_fields = ("created_at",)


class AssignmentAdmin(admin.ModelAdmin):
    list_display = fields = ("id", "created_at", "hit", "worker", "stage", "call_started_at", "words_to_pronounce")
    readonly_fields = ("created_at",)


admin.site.register(HIT, HITAdmin)
admin.site.register(Worker, WorkerAdmin)
admin.site.register(Assignment, AssignmentAdmin)
