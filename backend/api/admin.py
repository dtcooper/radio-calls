from django.contrib import admin

from .models import HIT


class HITAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "topic", "location")


admin.site.register(HIT, HITAdmin)
