from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from apps.api.views import ApiRootView
from apps.api.token_views import ObtainTokenView, RefreshTokenView, RevokeTokenView
from apps.api import resource_views

app_name = "api_v1"

urlpatterns = [
    path("", ApiRootView.as_view(), name="root"),
    path("auth/token/", ObtainTokenView.as_view(), name="token_obtain"),
    path("auth/token/refresh/", RefreshTokenView.as_view(), name="token_refresh"),
    path("auth/token/revoke/", RevokeTokenView.as_view(), name="token_revoke"),
    path("donors/", resource_views.DonorSearchApiView.as_view(), name="donor_list"),
    path("donors/<uuid:donor_id>/", resource_views.DonorDetailApiView.as_view(), name="donor_detail"),
    path("blood-requests/", resource_views.BloodRequestListCreateApiView.as_view(), name="blood_request_list"),
    path("blood-requests/<uuid:request_id>/", resource_views.BloodRequestDetailApiView.as_view(), name="blood_request_detail"),
    path("blood-requests/<uuid:request_id>/<str:action>/", resource_views.BloodRequestTransitionApiView.as_view(), name="blood_request_transition"),
    path("contact-requests/", resource_views.ContactRequestListCreateApiView.as_view(), name="contact_request_list"),
    path("contact-requests/<uuid:contact_request_id>/", resource_views.ContactRequestDetailApiView.as_view(), name="contact_request_detail"),
    path("contact-requests/<uuid:contact_request_id>/<str:action>/", resource_views.ContactRequestTransitionApiView.as_view(), name="contact_request_action"),
    path("connections/", resource_views.ConnectionListApiView.as_view(), name="connection_list"),
    path("connections/<uuid:connection_id>/", resource_views.ConnectionDetailApiView.as_view(), name="connection_detail"),
    path("connections/<uuid:connection_id>/<str:action>/", resource_views.ConnectionTransitionApiView.as_view(), name="connection_action"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
]
