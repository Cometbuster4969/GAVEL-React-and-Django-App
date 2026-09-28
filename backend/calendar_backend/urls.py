from django.http import JsonResponse
from django.urls import include, path, re_path
from rest_framework.decorators import api_view

from apps.shared.views import health, not_found, route_not_found


@api_view(["GET", "POST", "PATCH", "PUT", "DELETE"])
def unknown_api_route(request, path):
    return route_not_found(request)


def landing_page(request):
    return JsonResponse({"service": "Gavel API", "health": "/api/v1/health"})


urlpatterns = [
    path("", landing_page),
    path("api/v1/health", health),
    path("api/v1/", include("apps.gavel.urls")),
    re_path(r"^api/v1/(?P<path>.*)$", unknown_api_route),
    re_path(r"^.*$", not_found),
]
