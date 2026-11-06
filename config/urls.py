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

from config.health import liveness, readiness

urlpatterns = [
    path("health/live/", liveness, name="health_live"),
    path("health/ready/", readiness, name="health_ready"),
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("app/", include("apps.donors.urls")),
    path("app/settings/", include("apps.governance.urls")),
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
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
