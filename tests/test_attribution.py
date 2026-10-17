from datetime import date
from decimal import Decimal

from ingest.verify_attribution import choose


def test_distinct_days_recency_and_npi_ties():
    d1, d2 = date(2009, 1, 1), date(2009, 2, 1)
    lines = [('1','001',d1,True,Decimal(10)), ('2','001',d1,True,Decimal(10)),
             ('3','003',d2,True,Decimal(20)), ('4','002',d2,True,Decimal(20))]
    assert choose(lines)[:2] == ('002', '001')


def test_unknown_zero_negative_allowed_and_missing_npi():
    d = date(2010, 1, 1)
    lines = [('1','001',d,True,None), ('2','002',d,False,Decimal(-1)),
             ('3','003',d,False,Decimal(0)), ('4',None,d,True,Decimal(100))]
    assert choose(lines)[:2] == ('001', '003')
    assert choose(lines[:1])[:2] == ('001', None)
    assert choose([])[:2] == (None, None)
