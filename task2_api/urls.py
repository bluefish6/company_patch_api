from django.urls import path

from .views import CompanyDetailView

urlpatterns = [
    path(
        "api/v1.0/company/<str:pid>", CompanyDetailView.as_view(), name="company-detail"
    ),
]
