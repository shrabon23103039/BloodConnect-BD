from django.urls import path

from apps.locations import views

app_name = "locations"

urlpatterns = [
    path("options/<str:level>/", views.child_options, name="child_options"),
]
