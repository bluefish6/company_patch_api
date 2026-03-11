from pytest_factoryboy import register

from .factories import (
    CompanyFactory,
    DirectorFactory,
    IdentityFileFactory,
    ShareholderFactory,
    TaxInfoFactory,
)

register(CompanyFactory)
register(DirectorFactory)
register(ShareholderFactory)
register(TaxInfoFactory)
register(IdentityFileFactory)
