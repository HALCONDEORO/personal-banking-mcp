import copy
from decimal import localcontext
import unittest
import transaction_analytics as a


def row(amount='-12.40',currency='EUR',status='booked',**kwargs):
    r={'amount':amount,'currency':currency,'currency_known':currency!='XXX','status':status,
       'date':'2026-11-19','date_source':'transaction_date','date_inferred':False,'description':'Fictional grocer'}
    r.update(kwargs);return r


class AnalyticsTests(unittest.TestCase):
    def test_decimal_exact_and_no_ambient_context_rounding(self):
        with localcontext() as c:
            c.prec=2
            result=a.summarize_transactions([row('0.1'),row('0.2'),row('-0.01')])
        t=result['totals'][0];self.assertEqual(t['inflow'],'0.3');self.assertEqual(t['outflow'],'0.01');self.assertEqual(t['net'],'0.29')
    def test_currency_and_pending_never_combine(self):
        r=a.summarize_transactions([row(),row(currency='GBP'),row(status='pending'),row(currency='XXX')])
        self.assertEqual(len(r['totals']),4)
        self.assertFalse(next(x for x in r['totals'] if x['currency']=='XXX')['currency_known'])
    def test_user_category_over_provider(self):
        r=a.summarize_transactions([row(user_category='Food',provider_category='Groceries')])
        self.assertEqual(r['categories'][0]['category'],'Food')
    def test_provider_category_fallback(self):
        r=a.summarize_transactions([row(user_category=None,provider_category='Groceries')])
        self.assertEqual(r['categories'][0]['category'],'Groceries')
    def test_uncategorized_fallback(self):
        self.assertEqual(a.summarize_transactions([row()])['categories'][0]['category'],'Uncategorized')
    def test_refund_not_subtracted_from_category_outflow(self):
        r=a.summarize_transactions([row('-20'),row('5')]);self.assertEqual(r['categories'][0]['outflow'],'20');self.assertEqual(r['totals'][0]['net'],'-15')
    def test_empty_explicit_incomplete_history(self):
        r=a.summarize_transactions([]);self.assertEqual(r['totals'],[]);self.assertEqual(r['history_completeness'],'not_verified');self.assertEqual(r['scope'],'supplied_rows_only')
    def test_no_deduplication_guess(self):
        r=a.summarize_transactions([row(),row()]);self.assertEqual(r['totals'][0]['count'],2);self.assertEqual(r['deduplication'],'not_performed')
    def test_unknown_and_inferred_dates_counted(self):
        r=a.summarize_transactions([row(date=None,date_source=None),row(date_source='booking_date',date_inferred=True)])
        self.assertEqual(r['unknown_date_rows'],1);self.assertEqual(r['inferred_date_rows'],1)
    def test_casefold_search(self):
        r=a.search_transactions([row(description='STRASSE'),row(description='Other')],query='straße')
        self.assertEqual(len(r['transactions']),1)
    def test_search_date_inclusive(self):
        r=a.search_transactions([row()],start='2026-11-19',end='2026-11-19');self.assertEqual(r['matched_in_input'],1)
    def test_date_filter_excludes_unknown(self):
        r=a.search_transactions([row(date=None,date_source=None)],start='2026-01-01');self.assertEqual(r['matched_in_input'],0)
    def test_search_returns_copies(self):
        records=[row()];r=a.search_transactions(records);r['transactions'][0]['amount']='999';self.assertEqual(records[0]['amount'],'-12.40')
    def test_search_limit_reports_truncation(self):
        r=a.search_transactions([row(),row()],limit=1);self.assertTrue(r['truncated']);self.assertEqual(r['matched_in_input'],2)
    def test_invalid_limits(self):
        for limit in [True,0,-1,101,'1']:
            with self.subTest(limit=limit),self.assertRaises(a.AnalyticsStopped):a.search_transactions([],limit=limit)
    def test_bad_query(self):
        for query in [None,[],1,'x'*257]:
            with self.subTest(query=query),self.assertRaises(a.AnalyticsStopped):a.search_transactions([],query=query)
    def test_invalid_date_filters(self):
        for kwargs in [{'start':'2026-02-30'},{'end':'2026-1-1'},{'start':'2027-01-01','end':'2026-01-01'}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(a.AnalyticsStopped):a.search_transactions([],**kwargs)
    def test_input_cap_and_type(self):
        for records in [None,(),{},[row()]*1001]:
            with self.subTest(kind=type(records)),self.assertRaises(a.AnalyticsStopped):a.summarize_transactions(records)
    def test_max_precision_sum(self):
        r=a.summarize_transactions([row('999999999999999.99999999')]*1000)
        self.assertEqual(r['totals'][0]['net'],'999999999999999999.99999000')
    def test_rejects_float_exponent_nonfinite_money(self):
        for value in [1.0,True,'1e3','NaN','Infinity','1.123456789','1000000000000000']:
            with self.subTest(value=value),self.assertRaises(a.AnalyticsStopped):a.summarize_transactions([row(value)])
    def test_invalid_currency_status_consistency(self):
        for kwargs in [{'currency':'eur'},{'currency_known':False},{'status':'BOOK'},{'status':[]},{'currency':'XXX','currency_known':True}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(a.AnalyticsStopped):a.summarize_transactions([row(**kwargs)])
    def test_date_provenance_rejected_if_inconsistent(self):
        for kwargs in [{'date':'2026-02-30'},{'date':None},{'date_source':None},{'date_source':[]},{'date_inferred':1},{'date_source':'booking_date'},{'date_inferred':True}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(a.AnalyticsStopped):a.summarize_transactions([row(**kwargs)])
    def test_unknown_fields_and_bad_labels(self):
        for kwargs in [{'iban':'synthetic-private'},{'user_category':''},{'provider_category':'x\ny'},{'user_category':[]},{'description':'x'*1025}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(a.AnalyticsStopped):a.summarize_transactions([row(**kwargs)])
    def test_no_mutation(self):
        records=[row(user_category='Food')];before=copy.deepcopy(records);a.summarize_transactions(records);self.assertEqual(records,before)
    def test_negative_zero_output_normalized(self):
        r=a.summarize_transactions([row('-0.00')]);self.assertEqual(r['totals'][0]['net'],'0.00');self.assertEqual(r['categories'],[])
    def test_generic_error_no_input_text(self):
        with self.assertRaises(a.AnalyticsStopped) as cm:a.summarize_transactions([row('PRIVATE-CANARY')])
        self.assertNotIn('PRIVATE-CANARY',str(cm.exception))

if __name__=='__main__':unittest.main()
