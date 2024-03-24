from django.contrib import admin
from django.urls import path

from ninja import NinjaAPI

api = NinjaAPI()
api.add_router("/", "api.api.router")


urlpatterns = [
    path("cmsadmin/", admin.site.urls),
    path("api/", api.urls)
]
