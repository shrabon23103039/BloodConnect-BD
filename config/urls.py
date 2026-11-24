"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from apps.connections import views as connection_views
from apps.accounts import views as account_views
from config.health import liveness, readiness
from config.views import home, location_demo

urlpatterns = [
    path("health/live/", liveness, name="health_live"),
    path("health/ready/", readiness, name="health_ready"),
    path("api/v1/", include("apps.api.urls")),
    path("admin/", admin.site.urls),
    path("accounts/google/login/", account_views.google_oauth_start, name="google_login"),
    path(
        "accounts/google/login/callback/",
        account_views.google_oauth_callback,
        name="google_callback",
    ),
    path("accounts/", include("apps.accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("location-demo/", location_demo, name="location_demo"),
    path("app/location-options/", include("apps.locations.urls")),
    path("app/requests/", include("apps.requests.urls")),
    path("app/contact-requests/", include("apps.connections.urls")),
    path("app/notifications/", include("apps.notifications.urls")),
    path("app/moderation/", include("apps.moderation.urls")),
    path("app/operations/", include("apps.analytics.urls")),
    path(
        "app/connections/<uuid:connection_id>/",
        connection_views.accepted_connection_detail,
        name="connection_detail",
    ),
    path("app/", include("apps.donors.urls")),
    path("app/settings/", include("apps.governance.urls")),
    path("", home, name="home"),
    path(
        "how-it-works/",
        TemplateView.as_view(template_name="pages/how_it_works.html"),
        name="how_it_works",
    ),
    path("privacy/", TemplateView.as_view(template_name="pages/privacy.html"), name="privacy"),
    path("safety/", TemplateView.as_view(template_name="pages/safety.html"), name="safety"),
    path("terms/", TemplateView.as_view(template_name="pages/terms.html"), name="terms"),
    path("contact/", TemplateView.as_view(template_name="pages/contact.html"), name="contact"),
]

handler400 = "config.views.bad_request"
handler403 = "config.views.permission_denied"
handler404 = "config.views.not_found"
handler500 = "config.views.server_error"
