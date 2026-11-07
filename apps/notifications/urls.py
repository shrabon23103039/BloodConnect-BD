from django.urls import path

from apps.notifications import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("<uuid:notification_id>/read/", views.mark_notification_read, name="read"),
]
