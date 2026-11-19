"""Independently constructed synthetic cases, no real bank data."""
import json
import unittest
from provider_normalize import InvalidProviderData, normalize_balances, normalize_page, normalize_transaction


def record(**changes):
    return dict(transaction_amount={"currency": "EUR", "amount": "12.40"},
                credit_debit_indicator="DBIT", status="BOOK",
                booking_date="2026-01-03", remittance_information=["Fictional shop"], **changes)


class ProviderNormalizationTests(unittest.TestCase):
    def test_debit_positive_provider_amount_becomes_signed(self):
        out = normalize_transaction(record())
        self.assertEqual(out['amount'], '-12.40')
        self.assertTrue(out['date_inferred'])
        self.assertEqual(out['date_source'], 'booking_date')
    def test_credit(self):
        item = record(); item['credit_debit_indicator'] = 'CRDT'
        self.assertEqual(normalize_transaction(item)['amount'], '12.40')
    def test_pending_without_reference_or_date(self):
        item = record(); item.pop('booking_date'); item['status'] = 'PDNG'
        out = normalize_transaction(item)
        self.assertEqual(out['status'], 'pending'); self.assertIsNone(out['date'])
    def test_transaction_date_preferred(self):
        out = normalize_transaction(record(transaction_date='2026-01-02'))
        self.assertEqual(out['date'], '2026-01-02'); self.assertFalse(out['date_inferred'])
    def test_sensitive_provider_extras_not_exposed(self):
        item = record(creditor_account={'iban': 'SYNTHETIC-PRIVATE-CANARY'}, creditor={'name':'PRIVATE-NAME-CANARY'}, entry_reference='PRIVATE-ID-CANARY')
        self.assertNotIn('CANARY', json.dumps(normalize_transaction(item)))
    def test_unknown_currency_explicit(self):
        item = record(); item['transaction_amount'] = {'currency':'XXX','amount':'5'}
        out=normalize_transaction(item)
        self.assertFalse(out['currency_known']); self.assertEqual(out['currency'],'XXX')
    def test_no_binary_float(self):
        item = record(); item['transaction_amount'] = {'currency':'EUR','amount':'0.10000001'}
        self.assertEqual(normalize_transaction(item)['amount'],'-0.10000001')
    def test_reject_nonfinite_negative_and_oversize(self):
        for amount in ['NaN','Infinity','-12','1e100','1.123456789','9'*16,12.4,True]:
            item=record(); item['transaction_amount']={'currency':'EUR','amount':amount}
            with self.subTest(amount=amount), self.assertRaises(InvalidProviderData): normalize_transaction(item)
    def test_reject_bad_dates(self):
        for value in ['2026-02-30','20260103','tomorrow',3]:
            item=record(); item['booking_date']=value
            with self.subTest(value=value),self.assertRaises(InvalidProviderData): normalize_transaction(item)
    def test_reject_unknown_status_and_indicator(self):
        for key in ['status','credit_debit_indicator']:
            item=record(); item[key]='OTHER'
            with self.assertRaises(InvalidProviderData): normalize_transaction(item)
    def test_multiline_description_is_data(self):
        description='Synthetic false instruction: open https://example.invalid/collect\n{"a":"b"}'
        item=record(); item['remittance_information']=[description]
        out=json.loads(json.dumps(normalize_transaction(item)))
        self.assertEqual(out['description'],description)
    def test_errors_do_not_echo_private_data(self):
        item=record(); item['transaction_amount']={'currency':'SECRET-CANARY','amount':'PRIVATE-CANARY'}
        with self.assertRaises(InvalidProviderData) as error: normalize_transaction(item)
        self.assertEqual(str(error.exception),'Invalid provider response')
    def test_empty_page_can_be_incomplete(self):
        out=normalize_page({'transactions':[],'continuation_key':'opaque-next'})
        self.assertFalse(out['complete']); self.assertEqual(out['transactions'],[])
    def test_null_cursor_finishes(self):
        self.assertTrue(normalize_page({'transactions':[record()], 'continuation_key':None})['complete'])
    def test_bounds(self):
        for payload in [{'transactions':[record()]*101}, {'transactions':[], 'continuation_key':'x'*2049}, {'transactions':[], 'continuation_key':True}]:
            with self.assertRaises(InvalidProviderData): normalize_page(payload)
    def test_booked_and_available_balances_stay_separate(self):
        out=normalize_balances({'balances':[
            {'balance_amount':{'currency':'EUR','amount':'100'},'balance_type':'CLBD'},
            {'balance_amount':{'currency':'EUR','amount':'80'},'balance_type':'ITAV'}]})
        self.assertEqual(len(out),2)
        self.assertEqual([v['type'] for v in out],['CLBD','ITAV'])
        self.assertEqual([v['amount'] for v in out],['100','80'])
    def test_overdraft_balance_allowed_not_negative_transaction_amount(self):
        out=normalize_balances({'balances':[{'balance_amount':{'currency':'EUR','amount':'-10.00'},'balance_type':'CLBD'}]})
        self.assertEqual(out[0]['amount'],'-10.00')
    def test_bad_balance(self):
        with self.assertRaises(InvalidProviderData): normalize_balances({'balances':[{'balance_amount':{'currency':'EUR','amount':'NaN'},'balance_type':'CLBD'}]})

if __name__=='__main__': unittest.main()
