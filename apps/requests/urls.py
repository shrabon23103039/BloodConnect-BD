from django.urls import path

from apps.requests import views

app_name = "requests"

urlpatterns = [
    path("", views.request_list, name="list"),
    path("new/", views.request_create, name="create"),
    path("<uuid:public_id>/", views.request_detail, name="detail"),
    path("<uuid:public_id>/edit/", views.request_edit, name="edit"),
    path("<uuid:public_id>/<str:target_status>/", views.request_transition, name="transition"),
]
