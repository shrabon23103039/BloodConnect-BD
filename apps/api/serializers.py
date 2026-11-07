"""Explicit allowlisted serializers for versioned API resources."""

from rest_framework import serializers

from apps.connections.models import ContactRequest
from apps.donors.models import DonorProfile
from apps.requests.models import BloodRequest


class TokenObtainSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(write_only=True, min_length=32, max_length=128)


class TokenPairSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField()


class BloodRequestWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodRequest
        fields = (
            "blood_group",
            "units_requested",
            "required_at",
            "division",
            "district",
            "upazila",
            "facility_name",
            "facility_address",
            "urgency",
            "description",
            "public_listing_enabled",
            "expires_at",
        )


class ContactRequestCreateSerializer(serializers.Serializer):
    donor_id = serializers.UUIDField()
    blood_request_id = serializers.UUIDField()
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)


class ContactRequestDetailSerializer(serializers.ModelSerializer):
    contact = serializers.SerializerMethodField()

    class Meta:
        model = ContactRequest
        fields = ("id", "status", "created_at", "expires_at", "message", "contact")
        read_only_fields = fields

    def get_contact(self, _instance) -> dict[str, str] | None:
        return self.context.get("contact")


class ConnectionReadSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    contact = serializers.DictField(allow_null=True)


class DonorSearchSerializer(serializers.ModelSerializer):
    division = serializers.CharField(source="division.name_en", read_only=True)
    district = serializers.CharField(source="district.name_en", read_only=True)
    upazila = serializers.CharField(source="upazila.name_en", read_only=True, allow_null=True)

    class Meta:
        model = DonorProfile
        fields = (
            "id",
            "public_alias",
            "blood_group",
            "availability_status",
            "division",
            "district",
            "upazila",
        )
        read_only_fields = fields


class BloodRequestReadSerializer(serializers.ModelSerializer):
    division = serializers.CharField(source="division.name_en", read_only=True)
    district = serializers.CharField(source="district.name_en", read_only=True)
    upazila = serializers.CharField(source="upazila.name_en", read_only=True, allow_null=True)

    class Meta:
        model = BloodRequest
        fields = (
            "id",
            "blood_group",
            "units_requested",
            "required_at",
            "division",
            "district",
            "upazila",
            "urgency",
            "status",
            "expires_at",
            "created_at",
        )
        read_only_fields = fields


class BloodRequestOwnerReadSerializer(BloodRequestReadSerializer):
    class Meta(BloodRequestReadSerializer.Meta):
        fields = BloodRequestReadSerializer.Meta.fields + (
            "facility_name",
            "facility_address",
            "description",
            "public_listing_enabled",
        )


class ContactRequestReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactRequest
        fields = ("id", "status", "created_at", "expires_at")
        read_only_fields = fields


class PaginatedDonorSearchSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = DonorSearchSerializer(many=True)


class PaginatedBloodRequestSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = BloodRequestReadSerializer(many=True)


class PaginatedContactRequestSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ContactRequestReadSerializer(many=True)


class PaginatedConnectionSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ConnectionReadSerializer(many=True)
