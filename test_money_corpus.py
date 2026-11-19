# SPDX-License-Identifier: MIT
# Test cases adapted from the invariants in EU-Open-Banking-MCP money.ts.
# Copyright (c) 2026 personal-finance-eu-mcp contributors
# Modifications Copyright (c) 2026 Marco Antonio Tevar Asensio
# See THIRD_PARTY_NOTICES.md and LICENSES/.
"""Exact-string corpus. No currency conversion, rounding or minor-unit inference."""
import unittest
import traceback
from decimal import localcontext
from provider_normalize import normalize_transaction, InvalidProviderData


def record(amount, currency='EUR', indicator='CRDT'):
    return {'transaction_amount': {'amount':amount,'currency':currency},
            'credit_debit_indicator':indicator,'status':'BOOK'}

class TestMoneyCorpus(unittest.TestCase):
    def test_exact_amount_strings(self):
        cases=[('0.10','EUR'),('9000','GBP'),('100','JPY'),('1.234','KWD'),
               ('1.23456789','EUR'),('999999999999999.12345678','EUR'),
               ('0.00000001','GBP'),('1.2345','XXX')]
        for amount,currency in cases:
            with self.subTest(amount=amount,currency=currency):
                out=normalize_transaction(record(amount,currency))
                self.assertEqual(out['amount'],amount)
                self.assertEqual(out['currency'],currency)
    def test_no_global_decimal_context_dependency(self):
        with localcontext() as context:
            context.prec=3
            self.assertEqual(normalize_transaction(record('123456789.12345678',indicator='DBIT'))['amount'],'-123456789.12345678')
    def test_debit_zero_not_negative(self):
        for amount in ['0','0.00','-0.00']:
            with self.subTest(amount=amount):
                out=normalize_transaction(record(amount,indicator='DBIT'))['amount']
                self.assertFalse(out.startswith('-'))
    def test_credit_zero_not_negative(self):
        self.assertEqual(normalize_transaction(record('-0.00'))['amount'],'0.00')
    def test_unknown_not_guessed_as_two_decimals(self):
        out=normalize_transaction(record('1.23456789','XXX'))
        self.assertFalse(out['currency_known']);self.assertEqual(out['amount'],'1.23456789')
    def test_bounds_and_forbidden_forms(self):
        for value in [True,1,1.5,None,'NaN','Infinity','1e2','+1','-1','0.000000001','1234567890123456',' 1','1\n']:
            with self.subTest(value=value),self.assertRaises(InvalidProviderData):normalize_transaction(record(value))
    def test_full_traceback_value_free(self):
        candidate=record('1');candidate['transaction_date']='PRIVATE-DATE-CANARY'
        try:normalize_transaction(candidate)
        except InvalidProviderData as error:
            text=''.join(traceback.format_exception(type(error),error,error.__traceback__))
            self.assertNotIn('PRIVATE-DATE-'+'CANARY',text)
        else:self.fail('Invalid date accepted')

if __name__=='__main__':unittest.main()
