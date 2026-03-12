from django.db import transaction
from rest_framework import serializers

from .models import ChangeType, Company, Director, IdentityFile, Shareholder, TaxInfo
from .services import company_svc, director_svc, shareholder_svc
from .services.changelog_svc import create_changelog


class IdentityFileSerializer(serializers.ModelSerializer):
    pid = serializers.CharField(required=True)

    class Meta:
        model = IdentityFile
        fields = ["pid"]


class TaxInfoSerializer(serializers.ModelSerializer):
    pid = serializers.CharField(required=False)

    class Meta:
        model = TaxInfo
        fields = ["pid", "tin", "country"]


class DirectorSerializer(serializers.ModelSerializer):
    pid = serializers.CharField(required=False)
    taxinfo = TaxInfoSerializer(many=True, required=False)
    identity_files = IdentityFileSerializer(many=True, required=False)

    class Meta:
        model = Director
        fields = ["pid", "full_name", "taxinfo", "identity_files"]

    # def create(self, validated_data):
    #     taxinfo_data = validated_data.pop("taxinfo", None)
    #     identity_files_data = validated_data.pop("identity_files", None)
    #     instance = super().create(validated_data)
    #     director_svc.sync_collections(
    #         director=instance, taxinfo=taxinfo_data, identity_files=identity_files_data
    #     )
    #
    #     return instance

    # def update(self, instance, validated_data):
    #     taxinfo_data = validated_data.pop("taxinfo", None)
    #     identity_files_data = validated_data.pop("identity_files", None)
    #     instance = super().update(instance, validated_data)
    #     director_svc.sync_collections(
    #         director=instance, taxinfo=taxinfo_data, identity_files=identity_files_data
    #     )
    #     return instance


class ShareholderSerializer(serializers.ModelSerializer):
    pid = serializers.CharField(required=False)
    identity_files = IdentityFileSerializer(many=True, required=False)

    class Meta:
        model = Shareholder
        fields = ["pid", "full_name", "percentage", "identity_files"]

    # def create(self, validated_data):
    #     identity_files_data = validated_data.pop("identity_files", None)
    #     instance = super().create(validated_data)
    #     shareholder_svc.sync_collections(
    #         shareholder=instance, identity_files=identity_files_data
    #     )
    #     return instance

    # def update(self, instance, validated_data):
    #     identity_files_data = validated_data.pop("identity_files", None)
    #     instance = super().update(instance, validated_data)
    #     shareholder_svc.sync_collections(
    #         shareholder=instance, identity_files=identity_files_data
    #     )
    #     return instance


class CompanySerializer(serializers.ModelSerializer):
    taxinfo = TaxInfoSerializer(many=True, required=False)
    directors = DirectorSerializer(many=True, required=False)
    shareholders = ShareholderSerializer(many=True, required=False)

    class Meta:
        model = Company
        fields = [
            "pid",
            "name",
            "date_of_incorporation",
            "taxinfo",
            "directors",
            "shareholders",
        ]
        read_only_fields = ["pid"]

    @transaction.atomic
    def update(self, instance, validated_data):
        old_repr = self.to_representation(instance)

        taxinfo_data = validated_data.pop("taxinfo", None)
        directors_data = validated_data.pop("directors", None)
        shareholders_data = validated_data.pop("shareholders", None)

        instance = super().update(instance, validated_data)

        company_svc.sync_collections(
            company=instance,
            taxinfo=taxinfo_data,
            directors=directors_data,
            shareholders=shareholders_data,
        )

        new_repr = self.to_representation(instance)
        create_changelog(
            ChangeType.UPDATED, instance, old_data=old_repr, new_data=new_repr
        )
        return instance
