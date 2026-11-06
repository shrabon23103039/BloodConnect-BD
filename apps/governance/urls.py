from django.urls import path

from apps.governance import views

app_name = "governance"

urlpatterns = [
    path("privacy/", views.privacy_settings, name="privacy_settings"),
]
