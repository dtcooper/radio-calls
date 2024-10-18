from dateutil.parser import parse as dateutil_parse

from django.conf import settings

from constance import config

from .constants import PHONE_MODES


BUILD_TIME = dateutil_parse(settings.BUILD_TIME)


def global_template_vars(request):
    context = {
        "GIT_REV": settings.GIT_REV,
        "BUILD_TIME": BUILD_TIME,
        "PHONE_MODE": dict(PHONE_MODES).get(config.PHONE_MODE),
    }
    return context
