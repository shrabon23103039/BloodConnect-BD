from django.urls import path

from apps.moderation import views

app_name = "moderation"

urlpatterns = [
    path("reports/", views.report_list, name="list"),
    path("reports/<uuid:report_id>/", views.report_detail, name="detail"),
    path("reports/<uuid:report_id>/transition/", views.report_transition, name="transition"),
]
