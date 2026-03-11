from django.core.management.base import BaseCommand
from django.db import transaction

from task2_api.models import (
    ChangeLog,
    Company,
    Director,
    IdentityFile,
    Shareholder,
    TaxInfo,
)


class Command(BaseCommand):
    help = "Seeds the database with a single company"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Cleaning database...")
        Company.objects.all().delete()
        IdentityFile.objects.all().delete()
        TaxInfo.objects.all().delete()
        Director.objects.all().delete()
        Shareholder.objects.all().delete()
        ChangeLog.objects.all().delete()

        self.stdout.write("Seeding data...")

        company = Company.objects.create(
            pid="2374910283749102",
            name="Start Company",
            date_of_incorporation="2020-01-01",
        )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully added Company with PID {company.pid}.")
        )
