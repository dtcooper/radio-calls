from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.conf import settings
from django.shortcuts import redirect

from ninja import NinjaAPI

api = NinjaAPI()
api.add_router("/", "api.api.router")


def index(request):
    if settings.DEBUG or request.user.is_staff:
        return redirect("admin:index")
    else:
        return HttpResponse("Nothing to see here.", content_type="text/plain")


urlpatterns = [path("", index), path("cmsadmin/", admin.site.urls), path("api/", api.urls)]
