# SPDX-License-Identifier: MIT
# Adapted category/summary pattern from guille-near/openbanking-mcp,
# commit d61e3ad67b60aa848d96887fd4d06dc3fefbd749, MIT.
# Text-search pattern also adapted from elcukro/bank-mcp, commit
# c6abad503b1ecec47e80108ef8d0c614da0f4de5, MIT.
# Changes: no SQL/database, bounded explicit normalized input, Decimal strings,
# currency/status/date provenance separation and no implicit history claim.
"""Pure summaries of explicitly supplied normalized transactions. No I/O."""
from datetime import date
from decimal import Context, Decimal, localcontext
import re


class AnalyticsStopped(ValueError):
    def __init__(self):super().__init__('Local transaction analysis stopped')


def _date(value):
    if type(value) is not str or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value) is None:
        raise AnalyticsStopped()
    bad=False
    try:date.fromisoformat(value)
    except ValueError:bad=True
    if bad:raise AnalyticsStopped()
    return value


def _label(value):
    if type(value) is not str or not 1<=len(value)<=120 or any(ord(c)<32 or ord(c)==127 for c in value):
        raise AnalyticsStopped()
    return value


def _rows(records):
    if type(records) is not list or len(records)>1000:raise AnalyticsStopped()
    out=[]
    required={'amount','currency','currency_known','status','date','date_source','date_inferred','description'}
    for record in records:
        if type(record) is not dict or not required<=set(record) or set(record)-required-{'user_category','provider_category'}:
            raise AnalyticsStopped()
        amount=record['amount'];currency=record['currency']
        if type(amount) is not str or re.fullmatch(r'-?[0-9]{1,15}(?:\.[0-9]{1,8})?',amount) is None:raise AnalyticsStopped()
        if type(currency) is not str or re.fullmatch(r'[A-Z]{3}',currency) is None:raise AnalyticsStopped()
        if type(record['currency_known']) is not bool or record['currency_known']!=(currency!='XXX'):raise AnalyticsStopped()
        if type(record['status']) is not str or record['status'] not in {'booked','pending'}:raise AnalyticsStopped()
        source=record['date_source'];inferred=record['date_inferred']
        if type(inferred) is not bool or (source is not None and type(source) is not str) or source not in {None,'transaction_date','booking_date','value_date'}:raise AnalyticsStopped()
        if record['date'] is None:
            if source is not None or inferred:raise AnalyticsStopped()
        else:
            _date(record['date'])
            if source is None or inferred!=(source!='transaction_date'):raise AnalyticsStopped()
        text=record['description']
        if type(text) is not str or len(text)>1024:raise AnalyticsStopped()
        for field in ['user_category','provider_category']:
            if record.get(field) is not None:_label(record[field])
        out.append((record,Decimal(amount)))
    return out


def search_transactions(records, *, query='', start=None, end=None, limit=50):
    """Casefolded substring search, inclusive dates, explicit selected-row scope.

    Date filter uses the supplied normalized date, including labeled fallbacks.
    Rows without dates are excluded by date filters, never assigned today.
    """
    if type(query) is not str or len(query)>256 or type(limit) is not int or not 1<=limit<=100:
        raise AnalyticsStopped()
    if start is not None:_date(start)
    if end is not None:_date(end)
    if start is not None and end is not None and start>end:raise AnalyticsStopped()
    matches=[]
    for record,_ in _rows(records):
        when=record['date']
        if query.casefold() not in record['description'].casefold():continue
        if (start is not None or end is not None) and when is None:continue
        if start is not None and when<start or end is not None and when>end:continue
        matches.append(dict(record))
    return {'transactions':matches[:limit], 'matched_in_input':len(matches),
            'truncated':len(matches)>limit, 'scope':'supplied_rows_only',
            'history_completeness':'not_verified', 'input_rows':len(records)}


def summarize_transactions(records):
    """No deduplication guesses: caller owns exact nonduplicated input scope.

    Pending and booked never combine. XXX is an unknown-currency bucket, not
    convertible money. Categories are labels from caller/provider, not inferred.
    A positive refund is inflow, not silently subtracted from category outflows.
    """
    groups={};categories={};unknown_dates=0;inferred_dates=0
    with localcontext(Context(prec=64)) as ctx:
        for record,amount in _rows(records):
            key=(record['currency'],record['status'])
            group=groups.setdefault(key,{'inflow':Decimal(0),'outflow':Decimal(0),'net':Decimal(0),'count':0})
            group['count']+=1;group['net']+=amount
            if amount>=0:group['inflow']+=amount
            else:group['outflow']+=amount.copy_abs()
            if record['date'] is None:unknown_dates+=1
            if record['date_inferred']:inferred_dates+=1
            if amount<0:
                category=record.get('user_category') or record.get('provider_category') or 'Uncategorized'
                ck=key+(category,);item=categories.setdefault(ck,{'outflow':Decimal(0),'count':0})
                item['outflow']+=amount.copy_abs();item['count']+=1
        def money(value):return format(value.copy_abs() if value.is_zero() else value,'f')
        totals=[{'currency':key[0],'currency_known':key[0]!='XXX','status':key[1],
                 **{k:money(v) if isinstance(v,Decimal) else v for k,v in value.items()}}
                for key,value in sorted(groups.items())]
        cats=[{'currency':key[0],'currency_known':key[0]!='XXX','status':key[1],'category':key[2],
               'outflow':money(value['outflow']),'count':value['count']}
              for key,value in sorted(categories.items())]
    return {'totals':totals,'categories':cats,'input_rows':len(records),
            'unknown_date_rows':unknown_dates,'inferred_date_rows':inferred_dates,
            'scope':'supplied_rows_only','history_completeness':'not_verified',
            'deduplication':'not_performed'}
