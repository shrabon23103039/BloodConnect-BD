"""Non-sensitive API version discovery endpoint."""

from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema


class ApiRootSerializer(serializers.Serializer):
    version = serializers.CharField()
    schema = serializers.CharField()


class ApiRootView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = ApiRootSerializer

    @extend_schema(responses=ApiRootSerializer)
    def get(self, request):
        return Response({"version": "v1", "schema": "/api/v1/schema/"})
