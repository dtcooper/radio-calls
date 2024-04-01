import logging

from django.conf import settings
from django.contrib import admin
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import path

from ninja import NinjaAPI
from ninja.errors import AuthenticationError, HttpError, ValidationError


logger = logging.getLogger("django")


api = NinjaAPI()
api.add_router("hit", "api.routers.hit_router")


def register_exec_handler(exception, code, message):
    @api.exception_handler(exception)
    def _(request, exc):
        logger.exception(exc)
        return api.create_response(request, {"success": False, "error": message}, status=code)


for exception, code, message in (
    (Exception, 500, "Unexpected error ocurred!"),
    (AuthenticationError, 401, "Access denied!"),
    (ValidationError, 422, "Client exchanged data with server in an unexpected or bad way"),
    (Http404, 404, "Something you're looking for was not found"),
):
    register_exec_handler(exception, code, message)


@api.exception_handler(HttpError)
def http_error_handler(request, exc):
    logger.exception(exc)
    return api.create_response(request, {"success": False, "error": exc.message}, status=exc.status_code)


def index(request):
    if settings.DEBUG or request.user.is_staff:
        return redirect("admin:index")
    else:
        return HttpResponse("Nothing to see here.", content_type="text/plain")


urlpatterns = [path("", index), path("cmsadmin/", admin.site.urls), path("api/", api.urls)]
