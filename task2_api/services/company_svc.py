from .director_svc import sync_directors
from .shareholder_svc import sync_shareholders
from .taxinfo_svc import sync_taxinfo


def sync_collections(company, taxinfo, directors, shareholders):
    sync_taxinfo(company, taxinfo)
    sync_directors(company=company, new_directors=directors)
    sync_shareholders(company=company, new_shareholders=shareholders)
