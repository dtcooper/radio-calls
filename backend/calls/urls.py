import logging

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import include, path, re_path

from api.apis import hit_api, twilio_api
from api.models import WorkerPageLoad


logger = logging.getLogger(f"calls.{__name__}")


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


def hit_passthrough(request):
    # Used to log workers and as a spam catcher
    page_load = {}
    for field in ("worker", "assignment", "hit"):
        value = request.GET.get(f"{field}Id")
        if value is None and (value := request.GET.get(f"amp;{field}Id")) is not None:
            page_load["has_amp_encoded"] = True
        if value is not None:
            page_load[f"{field}_amazon_id"] = value

    if "worker_amazon_id" in page_load:
        worker_id, has_amp_encoded = page_load["worker_amazon_id"], "has_amp_encoded" in page_load
        logger.info(f"Worker {worker_id} loaded page, logging{' (had amp encoded)' if has_amp_encoded else ''}")
        WorkerPageLoad.objects.create(**page_load)

    return HttpResponse(headers={"X-Accel-Redirect": f"/__hit_passthrough__{request.path}"})


admin.site.site_title = admin.site.site_header = "Radio Calls"
admin.site.index_title = "Administration"
admin.site.site_url = None


urlpatterns = [
    path("", index),
    re_path("^hit/", hit_passthrough, name="hit_passthrough"),
    path("api/hit/", hit_api.urls),
    path("api/twilio/", twilio_api.urls),
    path("cmsadmin/mturk-manage/", mturk_manage, name="mturk_manage"),
    path("cmsadmin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
