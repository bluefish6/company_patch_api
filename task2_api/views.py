from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response

from .models import Company
from .serializers import CompanySerializer


class CompanyDetailView(generics.RetrieveUpdateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    lookup_field = "pid"

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        try:
            instance = Company.objects.select_for_update().get(pid=kwargs.get("pid"))
        except Company.DoesNotExist:
            return Response(
                {"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)
