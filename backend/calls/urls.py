from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import path

from api.apis import hit_api, twilio_api


def index(request):
    if settings.DEBUG or request.user.is_staff:
        return redirect("admin:index")
    else:
        return HttpResponse("Nothing to see here.", content_type="text/plain")


urlpatterns = [
    path("", index),
    path("cmsadmin/", admin.site.urls),
    path("api/hit/", hit_api.urls),
    path("api/twilio/", twilio_api.urls),
]
