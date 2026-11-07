from django.urls import path

from apps.connections import views

app_name = "connections"

urlpatterns = [
    path("", views.contact_request_home, name="home"),
    path("new/", views.create_contact_request_view, name="create"),
    path("incoming/", views.incoming_contact_requests, name="incoming"),
    path("outgoing/", views.outgoing_contact_requests, name="outgoing"),
    path(
        "incoming/<uuid:contact_request_id>/",
        views.incoming_contact_request_detail,
        name="incoming_detail",
    ),
    path(
        "outgoing/<uuid:contact_request_id>/",
        views.outgoing_contact_request_detail,
        name="outgoing_detail",
    ),
    path(
        "<uuid:contact_request_id>/<str:action>/",
        views.contact_request_action,
        name="action",
    ),
]
