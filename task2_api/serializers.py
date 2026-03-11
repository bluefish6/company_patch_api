from collections import defaultdict

from django.db import transaction
from rest_framework import serializers

from .models import Company, Director, IdentityFile, Shareholder, TaxInfo
from .services.changelog import ChangeType, create_changelog
from .services.orphans import (
    cleanup_potential_orphans,
    extend_potential_orphans,
)


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


class BaseNestedSerializer(serializers.ModelSerializer):

    def _sync_collection(
        self, parent_instance, collection_name: str, serializer_class, input_data
    ):
        if input_data is None:
            return

        parent_relation_manager = getattr(parent_instance, collection_name)
        model_class = serializer_class.Meta.model

        existing_items = {obj.pid: obj for obj in parent_relation_manager.all()}
        wanted_pids = [item.get("pid") for item in input_data if item.get("pid")]
        obsolete_items = [
            obj for obj in existing_items.values() if obj.pid not in wanted_pids
        ]
        potential_orphans: defaultdict[str, set] = defaultdict(set)

        # remove obsolete items
        for obj in obsolete_items:
            potential_orphans = extend_potential_orphans(potential_orphans, obj)
            if hasattr(parent_relation_manager, "remove"):
                parent_relation_manager.remove(obj)  # for 2-way relations
            else:
                create_changelog(ChangeType.REMOVED, obj)
                obj.delete()  # for objects accessible only from parent

        # update existing or create new items
        for data in input_data:
            pid = data.get("pid")
            if pid and pid in existing_items:
                # update existing items associated with current parent
                obj = existing_items[pid]
                potential_orphans = extend_potential_orphans(potential_orphans, obj)
                old_data = serializer_class(obj).data
                serializer = serializer_class(instance=obj, data=data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                create_changelog(
                    ChangeType.UPDATED, obj, old_data=old_data, new_data=serializer.data
                )
            else:
                # create new items or reuse existing, but not associated with current parent, then associate them
                if model_class in [IdentityFile, TaxInfo]:
                    obj, created = model_class.objects.get_or_create(
                        pid=pid, defaults={k: v for k, v in data.items() if k != "pid"}
                    )
                    if not created:
                        # if objects were already used elsewhere and here we're only updating them
                        serializer = serializer_class(
                            instance=obj, data=data, partial=True
                        )
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

                    parent_relation_manager.add(obj)
                    action = ChangeType.ADDED if created else ChangeType.UPDATED
                    create_changelog(action, obj, new_data=serializer_class(obj).data)
                elif model_class in [Director, Shareholder]:
                    serializer = serializer_class(data=data)
                    serializer.is_valid(raise_exception=True)
                    obj = serializer.save(company=parent_instance)
                    create_changelog(ChangeType.ADDED, obj, new_data=serializer.data)
                else:
                    raise NotImplementedError
        cleanup_potential_orphans(potential_orphans)


class DirectorSerializer(BaseNestedSerializer):
    pid = serializers.CharField(required=False)
    taxinfo = TaxInfoSerializer(many=True, required=False)
    identity_files = IdentityFileSerializer(many=True, required=False)

    class Meta:
        model = Director
        fields = ["pid", "full_name", "taxinfo", "identity_files"]

    def create(self, validated_data):
        taxinfo_data = validated_data.pop("taxinfo", None)
        identity_files_data = validated_data.pop("identity_files", None)
        instance = super().create(validated_data)
        self._sync_collection(instance, "taxinfo", TaxInfoSerializer, taxinfo_data)
        self._sync_collection(
            instance, "identity_files", IdentityFileSerializer, identity_files_data
        )
        return instance

    def update(self, instance, validated_data):
        taxinfo_data = validated_data.pop("taxinfo", None)
        identity_files_data = validated_data.pop("identity_files", None)
        instance = super().update(instance, validated_data)
        self._sync_collection(instance, "taxinfo", TaxInfoSerializer, taxinfo_data)
        self._sync_collection(
            instance, "identity_files", IdentityFileSerializer, identity_files_data
        )
        return instance


class ShareholderSerializer(BaseNestedSerializer):
    pid = serializers.CharField(required=False)
    identity_files = IdentityFileSerializer(many=True, required=False)

    class Meta:
        model = Shareholder
        fields = ["pid", "full_name", "percentage", "identity_files"]

    def create(self, validated_data):
        identity_files_data = validated_data.pop("identity_files", None)
        instance = super().create(validated_data)
        self._sync_collection(
            instance, "identity_files", IdentityFileSerializer, identity_files_data
        )
        return instance

    def update(self, instance, validated_data):
        identity_files_data = validated_data.pop("identity_files", None)
        instance = super().update(instance, validated_data)
        self._sync_collection(
            instance, "identity_files", IdentityFileSerializer, identity_files_data
        )
        return instance


class CompanySerializer(BaseNestedSerializer):
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

        self._sync_collection(instance, "taxinfo", TaxInfoSerializer, taxinfo_data)
        self._sync_collection(instance, "directors", DirectorSerializer, directors_data)
        self._sync_collection(
            instance, "shareholders", ShareholderSerializer, shareholders_data
        )

        new_repr = self.to_representation(instance)
        create_changelog(
            ChangeType.UPDATED, instance, old_data=old_repr, new_data=new_repr
        )
        return instance
