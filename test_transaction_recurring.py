import copy
import unittest
from decimal import getcontext, setcontext
from transaction_recurring import recurring_charge_candidates as find
from transaction_analytics import AnalyticsStopped


def row(when='2026-01-15', **changes):
    return dict(amount='-9.99', currency='EUR', currency_known=True,
                status='booked', date=when, date_source='transaction_date',
                date_inferred=False, description='Fictional monthly service', **changes)


def series():
    return [row(when) for when in ['2026-01-15', '2026-02-15', '2026-03-15']]


class RecurringTests(unittest.TestCase):
    def test_explainable_candidate_and_no_prediction(self):
        result = find(series()); c = result['candidates'][0]
        self.assertEqual(c['interval_days'], [31, 28])
        self.assertEqual(c['amount_magnitude'], '9.99')
        self.assertEqual(c['distinct_date_count'], 3)
        self.assertEqual(c['certainty'], 'unverified_pattern')
        self.assertEqual(result['future_charge'], 'not_predicted')
        self.assertEqual(result['obligation'], 'not_determined')
        self.assertEqual(result['merchant_identity'], 'not_verified')

    def test_empty_and_two_dates_not_candidates(self):
        self.assertEqual(find([])['candidates'], [])
        self.assertEqual(find(series()[:2])['candidates'], [])

    def test_repeated_input_cannot_manufacture_distinct_dates(self):
        rows = [row()] * 10
        self.assertEqual(find(rows)['candidates'], [])
        rows = series() + [row()]
        c = find(rows)['candidates'][0]
        self.assertEqual(c['distinct_date_count'], 3)
        self.assertEqual(c['supporting_input_rows'], 4)
        self.assertEqual(find(rows)['deduplication'], 'not_performed')

    def test_pending_never_joins_booked(self):
        rows = series(); rows[2]['status'] = 'pending'
        result = find(rows)
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['excluded_rows_by_first_reason']['pending'], 1)

    def test_unknown_currency_excluded(self):
        rows = series()
        for r in rows:r.update(currency='XXX', currency_known=False)
        self.assertEqual(find(rows)['candidates'], [])

    def test_currencies_never_combine(self):
        rows = series(); rows[-1]['currency'] = 'GBP'
        self.assertEqual(find(rows)['candidates'], [])
        other = copy.deepcopy(series())
        for r in other:r['currency'] = 'GBP'
        self.assertEqual(len(find(series()+other)['candidates']), 2)

    def test_exact_description_not_merchant_guess(self):
        for text in ['fictional monthly service', 'Fictional monthly service ',
                     'Fictional monthly service 123']:
            rows = series(); rows[-1]['description'] = text
            self.assertEqual(find(rows)['candidates'], [])

    def test_text_is_data_not_instruction(self):
        rows = series()
        for r in rows:r['description'] = '<script>synthetic text</script>'
        self.assertEqual(find(rows)['candidates'][0]['description'], rows[0]['description'])

    def test_empty_description_excluded(self):
        rows = series()
        for r in rows:r['description'] = '  '
        self.assertEqual(find(rows)['candidates'], [])

    def test_positive_zero_and_negative_zero_excluded(self):
        for amount in ['9.99', '0', '-0.00']:
            rows = series()
            for r in rows:r['amount'] = amount
            self.assertEqual(find(rows)['candidates'], [])

    def test_original_date_required(self):
        for change in [dict(date=None,date_source=None,date_inferred=False),
                       dict(date_source='booking_date', date_inferred=True),
                       dict(date_source='value_date', date_inferred=True)]:
            rows=series(); rows[0].update(change)
            self.assertEqual(find(rows)['candidates'], [])

    def test_every_gap_not_median(self):
        rows=[row(d) for d in ['2026-01-01','2026-01-31','2026-03-02','2026-06-01']]
        self.assertEqual(find(rows)['candidates'], [])

    def test_boundaries_25_and_35_included(self):
        rows=[row(d) for d in ['2026-01-01','2026-01-26','2026-03-02']]
        self.assertEqual(find(rows)['candidates'][0]['interval_days'], [25,35])

    def test_24_and_36_excluded(self):
        for dates in [['2026-01-01','2026-01-25','2026-02-24'],
                      ['2026-01-01','2026-02-06','2026-03-08']]:
            self.assertEqual(find([row(d) for d in dates])['candidates'], [])

    def test_trailing_scale_groups_without_ambient_context_dependency(self):
        rows=series(); rows[0]['amount']='-9.99000000'
        baseline=find(rows); old=getcontext().copy()
        try:
            getcontext().prec=1
            for signal in getcontext().traps:getcontext().traps[signal]=True
            self.assertEqual(find(rows),baseline)
        finally:setcontext(old)

    def test_different_amount_does_not_average_or_predict(self):
        rows=series();rows[-1]['amount']='-10.00'
        self.assertEqual(find(rows)['candidates'], [])

    def test_input_order_not_result_order(self):
        self.assertEqual(find(series()),find(list(reversed(series()))))

    def test_input_not_mutated(self):
        rows=series();before=copy.deepcopy(rows);find(rows)
        self.assertEqual(rows,before)

    def test_invalid_input_sanitized(self):
        for rows in [None,(),[{}],series()*334]:
            with self.assertRaisesRegex(AnalyticsStopped,'^Local transaction analysis stopped$'):
                find(rows)
        rows=series();rows[0]['private_extra']='CANARY_NOT_AN_ERROR'
        with self.assertRaises(AnalyticsStopped) as got:find(rows)
        self.assertNotIn('CANARY',str(got.exception))

    def test_output_contains_only_nominated_fields_not_categories(self):
        rows=series()
        for r in rows:r['provider_category']='Private caller label'
        self.assertNotIn('Private caller label',str(find(rows)))


if __name__ == '__main__':unittest.main()
