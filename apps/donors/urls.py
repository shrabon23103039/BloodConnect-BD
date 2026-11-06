from django.urls import path

from apps.donors import views

app_name = "donors"

urlpatterns = [
    path("donor-profile/", views.donor_profile_editor, name="profile"),
]
