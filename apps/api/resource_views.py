"""Paginated API resource endpoints backed by existing domain services."""

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import AccountRole, has_role
from apps.accounts.throttling import limited_by_ip
from apps.api.serializers import (
    BloodRequestOwnerReadSerializer,
    BloodRequestReadSerializer,
    BloodRequestWriteSerializer,
    ConnectionReadSerializer,
    ContactRequestCreateSerializer,
    ContactRequestDetailSerializer,
    ContactRequestReadSerializer,
    DonorSearchSerializer,
    PaginatedBloodRequestSerializer,
    PaginatedConnectionSerializer,
    PaginatedContactRequestSerializer,
    PaginatedDonorSearchSerializer,
)
from apps.connections.models import Connection, ConnectionStatus, ContactRequest, ContactRequestStatus
from apps.connections.services import (
    create_contact_request,
    get_disclosed_contact_channels,
    transition_connection,
    transition_contact_request,
)
from apps.donors.models import AvailabilityStatus, DonorProfile
from apps.donors.search_forms import DonorSearchForm
from apps.requests.models import BloodRequest, BloodRequestStatus
from apps.requests.services import create_blood_request, transition_blood_request, update_blood_request


def _raise_validation(error):
    if getattr(error, "message_dict", None):
        raise ValidationError(error.message_dict) from error
    raise ValidationError(getattr(error, "messages", [str(error)])) from error


def _require_active(user):
    if not user.is_authenticated:
        raise NotAuthenticated("Authentication is required.")
    if not has_role(user, AccountRole.AUTHENTICATED_USER):
        raise PermissionDenied("An active account is required.")


def _connection_payload(connection, user):
    channels = None
    if (
        connection.status == ConnectionStatus.ACTIVE
        and connection.contact_request.status == ContactRequestStatus.ACCEPTED
        and connection.contact_request.recipient_id == user.pk
    ):
        channels = get_disclosed_contact_channels(
            recipient=user,
            connection_id=connection.pk,
        ) or None
    return ConnectionReadSerializer({
        "id": connection.pk,
        "status": connection.status,
        "created_at": connection.created_at,
        "contact": channels,
    }).data


class DonorSearchApiView(APIView):
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination

    @limited_by_ip(scope="api-donor-search", limit=30, window_seconds=60, api_response=True)
    @extend_schema(operation_id="donor_search_list", responses=PaginatedDonorSearchSerializer)
    def get(self, request):
        form = DonorSearchForm(request.query_params or None)
        if form.is_bound and not form.is_valid():
            raise ValidationError(form.errors)
        profiles = DonorProfile.objects.discoverable().filter(
            availability_status=AvailabilityStatus.AVAILABLE
        )
        if form.is_bound:
            for field in ("blood_group", "division", "district", "upazila"):
                value = form.cleaned_data.get(field)
                if value:
                    profiles = profiles.filter(**{field: value})
        profiles = profiles.select_related("division", "district", "upazila").order_by(
            "district__name_en", "public_alias", "id"
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(profiles, request, view=self)
        return paginator.get_paginated_response(DonorSearchSerializer(page, many=True).data)


class DonorDetailApiView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(operation_id="donor_search_detail", responses=DonorSearchSerializer)
    def get(self, request, donor_id):
        profile = get_object_or_404(
            DonorProfile.objects.discoverable().select_related("division", "district", "upazila"),
            pk=donor_id,
            availability_status=AvailabilityStatus.AVAILABLE,
        )
        return Response(DonorSearchSerializer(profile).data)


class BloodRequestListCreateApiView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(operation_id="blood_request_list", responses=PaginatedBloodRequestSerializer)
    def get(self, request):
        requests = BloodRequest.objects.filter(
            status=BloodRequestStatus.OPEN,
            public_listing_enabled=True,
            expires_at__gt=timezone.now(),
        ).select_related("division", "district", "upazila").order_by("-created_at", "id")
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(requests, request, view=self)
        return paginator.get_paginated_response(BloodRequestReadSerializer(page, many=True).data)

    @extend_schema(
        operation_id="blood_request_create",
        request=BloodRequestWriteSerializer,
        responses={201: BloodRequestOwnerReadSerializer},
    )
    def post(self, request):
        _require_active(request.user)
        return self._create(request)

    @limited_by_ip(
        scope="api-blood-request-create",
        limit=10,
        window_seconds=3600,
        api_response=True,
    )
    def _create(self, request):
        _require_active(request.user)
        serializer = BloodRequestWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            blood_request = create_blood_request(
                user=request.user,
                values=serializer.validated_data,
                publish=True,
            )
        except DjangoValidationError as error:
            _raise_validation(error)
        return Response(
            BloodRequestOwnerReadSerializer(blood_request).data,
            status=status.HTTP_201_CREATED,
        )


class BloodRequestDetailApiView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(operation_id="blood_request_detail", responses=BloodRequestOwnerReadSerializer)
    def get(self, request, request_id):
        queryset = BloodRequest.objects.select_related("division", "district", "upazila").filter(
            status=BloodRequestStatus.OPEN,
            public_listing_enabled=True,
            expires_at__gt=timezone.now(),
        )
        if request.user.is_authenticated:
            _require_active(request.user)
            queryset = BloodRequest.objects.select_related(
                "division", "district", "upazila"
            ).filter(
                Q(
                    status=BloodRequestStatus.OPEN,
                    public_listing_enabled=True,
                    expires_at__gt=timezone.now(),
                )
                | Q(requester=request.user)
            )
        blood_request = get_object_or_404(queryset, pk=request_id)
        is_owner = request.user.is_authenticated and blood_request.requester_id == request.user.pk
        if is_owner:
            return Response(BloodRequestOwnerReadSerializer(blood_request).data)
        return Response(BloodRequestReadSerializer(blood_request).data)

    @extend_schema(
        operation_id="blood_request_update",
        request=BloodRequestWriteSerializer,
        responses=BloodRequestOwnerReadSerializer,
    )
    def patch(self, request, request_id):
        _require_active(request.user)
        serializer = BloodRequestWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            blood_request = update_blood_request(
                user=request.user,
                blood_request_id=request_id,
                values=serializer.validated_data,
            )
        except (DjangoPermissionDenied, DjangoValidationError) as error:
            if isinstance(error, DjangoPermissionDenied):
                raise PermissionDenied(str(error)) from error
            _raise_validation(error)
        return Response(BloodRequestOwnerReadSerializer(blood_request).data)


class BloodRequestTransitionApiView(APIView):
    permission_classes = [IsAuthenticated]
    transitions = {"cancel": BloodRequestStatus.CANCELLED, "close": BloodRequestStatus.FULFILLED}

    @extend_schema(operation_id="blood_request_transition", request=None, responses=BloodRequestReadSerializer)
    def post(self, request, request_id, action):
        _require_active(request.user)
        target = self.transitions.get(action)
        if target is None:
            raise NotFound("Unsupported action.")
        try:
            blood_request = transition_blood_request(
                user=request.user,
                blood_request_id=request_id,
                target_status=target,
            )
        except DjangoPermissionDenied as error:
            raise PermissionDenied(str(error)) from error
        except DjangoValidationError as error:
            _raise_validation(error)
        return Response(BloodRequestReadSerializer(blood_request).data)


class ContactRequestListCreateApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="contact_request_list", responses=PaginatedContactRequestSerializer)
    def get(self, request):
        _require_active(request.user)
        direction = request.query_params.get("direction")
        if direction == "incoming":
            queryset = ContactRequest.objects.filter(donor_profile__user=request.user)
        elif direction == "outgoing":
            queryset = ContactRequest.objects.filter(recipient=request.user)
        else:
            raise ValidationError({"direction": "Choose incoming or outgoing."})
        queryset = queryset.order_by("-created_at", "id")
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ContactRequestReadSerializer(page, many=True).data)

    @limited_by_ip(
        scope="api-contact-create",
        limit=10,
        window_seconds=3600,
        api_response=True,
    )
    @extend_schema(
        operation_id="contact_request_create",
        request=ContactRequestCreateSerializer,
        responses={201: ContactRequestDetailSerializer},
    )
    def post(self, request):
        _require_active(request.user)
        serializer = ContactRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            contact_request = create_contact_request(
                recipient=request.user,
                donor_profile_id=data["donor_id"],
                blood_request_id=data["blood_request_id"],
                message=data.get("message", ""),
            )
        except DjangoValidationError as error:
            _raise_validation(error)
        return Response(
            ContactRequestDetailSerializer(contact_request).data,
            status=status.HTTP_201_CREATED,
        )


def _get_contact_request_for_participant(request, contact_request_id):
    _require_active(request.user)
    contact_request = ContactRequest.objects.select_related(
        "donor_profile", "donor_profile__user"
    ).filter(pk=contact_request_id).first()
    if contact_request is None or not (
        contact_request.recipient_id == request.user.pk
        or contact_request.donor_profile.user_id == request.user.pk
    ):
        from rest_framework.exceptions import NotFound

        raise NotFound("Contact request not found.")
    return contact_request


class ContactRequestDetailApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="contact_request_detail", responses=ContactRequestDetailSerializer)
    def get(self, request, contact_request_id):
        contact_request = _get_contact_request_for_participant(request, contact_request_id)
        channels = None
        if (
            contact_request.recipient_id == request.user.pk
            and contact_request.status == ContactRequestStatus.ACCEPTED
        ):
            connection = getattr(contact_request, "connection", None)
            if connection:
                channels = get_disclosed_contact_channels(
                    recipient=request.user,
                    connection_id=connection.pk,
                ) or None
        return Response(ContactRequestDetailSerializer(contact_request, context={"contact": channels}).data)



class ContactRequestTransitionApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="contact_request_transition",
        request=None,
        responses=ContactRequestDetailSerializer,
    )
    def post(self, request, contact_request_id, action):
        contact_request = _get_contact_request_for_participant(request, contact_request_id)
        transitions = {
            "accept": ContactRequestStatus.ACCEPTED,
            "decline": ContactRequestStatus.DECLINED,
            "cancel": ContactRequestStatus.CANCELLED,
        }
        target = transitions.get(action)
        if target is None:
            raise NotFound("Unsupported action.")
        try:
            updated = transition_contact_request(
                user=request.user,
                contact_request_id=contact_request.pk,
                target_status=target,
            )
        except DjangoPermissionDenied as error:
            raise PermissionDenied(str(error)) from error
        except DjangoValidationError as error:
            _raise_validation(error)
        channels = None
        if (
            updated.recipient_id == request.user.pk
            and updated.status == ContactRequestStatus.ACCEPTED
            and getattr(updated, "connection", None)
        ):
            channels = get_disclosed_contact_channels(
                recipient=request.user,
                connection_id=updated.connection.pk,
            ) or None
        return Response(ContactRequestDetailSerializer(updated, context={"contact": channels}).data)


class ConnectionListApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="connection_list", responses=PaginatedConnectionSerializer)
    def get(self, request):
        _require_active(request.user)
        connections = Connection.objects.select_related("contact_request").filter(
            Q(contact_request__recipient=request.user)
            | Q(contact_request__donor_profile__user=request.user)
        ).order_by("-created_at", "id")
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(connections, request, view=self)
        return paginator.get_paginated_response([
            _connection_payload(connection, request.user) for connection in page
        ])


class ConnectionDetailApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="connection_detail", responses=ConnectionReadSerializer)
    def get(self, request, connection_id):
        _require_active(request.user)
        connection = get_object_or_404(
            Connection.objects.select_related("contact_request", "contact_request__donor_profile"),
            Q(pk=connection_id)
            & (
                Q(contact_request__recipient=request.user)
                | Q(contact_request__donor_profile__user=request.user)
            ),
        )
        return Response(_connection_payload(connection, request.user))

class ConnectionTransitionApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="connection_transition",
        request=None,
        responses=ConnectionReadSerializer,
    )
    def post(self, request, connection_id, action):
        _require_active(request.user)
        if action != "close":
            raise NotFound("Unsupported action.")
        try:
            connection = transition_connection(user=request.user, connection_id=connection_id)
        except DjangoPermissionDenied as error:
            raise PermissionDenied(str(error)) from error
        except DjangoValidationError as error:
            _raise_validation(error)
        connection = Connection.objects.select_related("contact_request").get(pk=connection.pk)
        return Response(_connection_payload(connection, request.user))
