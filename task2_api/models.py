import random
from enum import StrEnum

from django.db import IntegrityError, models, transaction


def generate_pid() -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(16)])


class PIDMixin(models.Model):
    pid = models.CharField(
        primary_key=True, max_length=16, default=generate_pid, editable=False
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self._state.adding:
            for attempt in range(3):
                try:
                    with transaction.atomic():
                        return super().save(*args, **kwargs)
                except IntegrityError:
                    # retry 3 times in case of collisions
                    if attempt == 2:
                        raise
                    self.pid = generate_pid()
        else:
            return super().save(*args, **kwargs)


class ChangeType(StrEnum):
    ADDED = "added"
    UPDATED = "updated"
    REMOVED = "removed"


class ChangeLog(models.Model):
    change_type = models.CharField(choices=ChangeType)
    object_type = models.CharField(db_index=True)
    object_pid = models.CharField(max_length=16, db_index=True)
    changes = models.JSONField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class IdentityFile(PIDMixin):
    pass

    def to_dict(self):
        return {"pid": self.pid}


class TaxInfo(PIDMixin):
    tin = models.CharField()
    country = models.CharField(max_length=2)

    def to_dict(self):
        return {"pid": self.pid, "tin": self.tin, "country": self.country}


class CompanyTaxInfo(models.Model):
    # association via separate table
    company = models.ForeignKey("Company", on_delete=models.CASCADE)
    taxinfo = models.ForeignKey("TaxInfo", on_delete=models.CASCADE)
    pk = models.CompositePrimaryKey("company", "taxinfo")

    class Meta:
        db_table = "task2_api_company_taxinfo"


class DirectorIdentityFile(models.Model):
    # association via separate table
    director_pid = models.ForeignKey("Director", on_delete=models.CASCADE)
    identityfile_pid = models.ForeignKey("IdentityFile", on_delete=models.CASCADE)
    pk = models.CompositePrimaryKey("director_pid", "identityfile_pid")

    class Meta:
        db_table = "task2_api_director_identity_files"


class DirectorTaxInfo(models.Model):
    # association via separate table
    director_pid = models.ForeignKey("Director", on_delete=models.CASCADE)
    taxinfo_pid = models.ForeignKey("TaxInfo", on_delete=models.CASCADE)
    pk = models.CompositePrimaryKey("director_pid", "taxinfo_pid")

    class Meta:
        db_table = "task2_api_director_taxinfo"


class ShareholderIdentityFile(models.Model):
    # association via separate table
    shareholder_pid = models.ForeignKey("Shareholder", on_delete=models.CASCADE)
    identity_file_pid = models.ForeignKey("IdentityFile", on_delete=models.CASCADE)
    pk = models.CompositePrimaryKey("shareholder_pid", "identity_file_pid")

    class Meta:
        db_table = "task2_api_shareholder_identity_files"


class Company(PIDMixin):
    name = models.CharField()
    date_of_incorporation = models.DateField()
    taxinfo = models.ManyToManyField(
        TaxInfo,
        related_name="companies",
        through=CompanyTaxInfo,
    )

    def to_dict(self):
        return {
            "pid": self.pid,
            "name": self.name,
            "date_of_incorporation": str(self.date_of_incorporation),
            "taxinfo": [t.to_dict() for t in self.taxinfo.all()],
            "directors": [d.to_dict() for d in self.directors.all()],
            "shareholders": [s.to_dict() for s in self.shareholders.all()],
        }


class Director(PIDMixin):
    company = models.ForeignKey(
        "Company", related_name="directors", on_delete=models.CASCADE
    )
    full_name = models.CharField()
    taxinfo = models.ManyToManyField(
        TaxInfo, related_name="directors", through=DirectorTaxInfo
    )
    identity_files = models.ManyToManyField(
        IdentityFile, related_name="directors", through=DirectorIdentityFile
    )

    def to_dict(self):
        return {
            "pid": self.pid,
            "full_name": self.full_name,
            "taxinfo": [x.to_dict() for x in self.taxinfo.all()],
            "identity_files": [x.to_dict() for x in self.identity_files.all()],
        }


class Shareholder(PIDMixin):
    full_name = models.CharField()
    percentage = models.IntegerField()
    company = models.ForeignKey(
        "Company", related_name="shareholders", on_delete=models.CASCADE
    )
    identity_files = models.ManyToManyField(
        IdentityFile, related_name="shareholders", through=ShareholderIdentityFile
    )

    def to_dict(self):
        return {
            "pid": self.pid,
            "full_name": self.full_name,
            "percentage": self.percentage,
            "identity_files": [x.to_dict() for x in self.identity_files.all()],
        }
