from dateutil.parser import parse as dateutil_parse

from django.conf import settings


BUILD_TIME = dateutil_parse(settings.BUILD_TIME)


def build_vars(request):
    return {"GIT_REV": settings.GIT_REV, "BUILD_TIME": BUILD_TIME}
