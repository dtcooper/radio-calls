from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import path

from api.apis import hit_api, twilio_api


def index(request):
    if request.user.has_perm("api.preview_hit"):
        return redirect("admin:index")
    return HttpResponse(
        "There are forty people in the world and five of them are hamburgers.", content_type="text/plain"
    )


def mturk_manage(request):
    if request.user.is_superuser:
        return render(
            request,
            "api/mturk_manage.html",
            {
                "AWS_ACCESS_KEY_ID": settings.AWS_ACCESS_KEY_ID,
                "AWS_SECRET_ACCESS_KEY": settings.AWS_SECRET_ACCESS_KEY,
            },
        )
    return HttpResponseForbidden()


admin.site.site_title = admin.site.site_header = "Radio Calls"
admin.site.index_title = "Administration"
admin.site.site_url = None


urlpatterns = [
    path("", index),
    path("api/hit/", hit_api.urls),
    path("api/twilio/", twilio_api.urls),
    path("cmsadmin/mturk-manage/", mturk_manage, name="mturk_manage"),
    path("cmsadmin/", admin.site.urls),
]
