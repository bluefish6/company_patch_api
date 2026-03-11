import factory

from task2_api.models import Company, Director, IdentityFile, Shareholder, TaxInfo


class IdentityFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IdentityFile


class TaxInfoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaxInfo

    tin = factory.Faker("numerify", text="##########")
    country = factory.Faker("country_code")


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company
        skip_postgeneration_save = True

    name = factory.Faker("company")
    date_of_incorporation = factory.Faker("date")

    @factory.post_generation
    def with_taxinfo(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for info in extracted:
                self.taxinfo.add(info)


class DirectorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Director
        skip_postgeneration_save = True

    full_name = factory.Faker("name")
    company = factory.SubFactory(CompanyFactory)

    @factory.post_generation
    def with_taxinfo(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for info in extracted:
                self.taxinfo.add(info)

    @factory.post_generation
    def with_identity_files(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for f in extracted:
                self.identity_files.add(f)


class ShareholderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Shareholder
        skip_postgeneration_save = True

    full_name = factory.Faker("name")
    percentage = factory.Faker("random_int", min=1, max=100)
    company = factory.SubFactory(CompanyFactory)

    @factory.post_generation
    def with_identity_files(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for f in extracted:
                self.identity_files.add(f)
