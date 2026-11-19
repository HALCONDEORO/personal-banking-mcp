# SPDX-License-Identifier: MIT
# Grouping/cadence pattern adapted from guille-near/openbanking-mcp,
# d61e3ad67b60aa848d96887fd4d06dc3fefbd749, MIT.
# Copyright (c) 2026 Guille Pérez
# Changes: pure supplied rows, exact description/currency/amount grouping,
# three distinct dates, every interval 25..35 days, no database/model/prediction.
"""Explainable fixed-amount monthly candidates, not confirmed subscriptions."""
from datetime import date
from decimal import Context, localcontext
from transaction_analytics import _rows


def recurring_charge_candidates(records):
    """Return uncertain patterns only, with no next-charge or obligation claim.

    Input contract is the analytics normalized-row contract (at most 1000).
    Only booked debits with known currency and original transaction dates enter.
    Exact nonempty description is a grouping label, NOT merchant identity.
    Equal Decimal amounts group despite harmless trailing zero differences.
    Multiple rows on one date do not count as separate recurrence evidence;
    this does not identify duplicate transactions or correct financial totals.
    All consecutive distinct-date intervals must be 25..35 days. Three dates
    are required. This intentionally misses variable/weekly/irregular charges.
    """
    groups = {}
    excluded = {'pending': 0, 'non_debit': 0, 'unknown_currency': 0,
                'unreliable_date': 0, 'empty_description': 0}
    with localcontext(Context(prec=64)):
        for row, amount in _rows(records):
            if row['status'] != 'booked':
                excluded['pending'] += 1
                continue
            if amount >= 0:
                excluded['non_debit'] += 1
                continue
            if not row['currency_known']:
                excluded['unknown_currency'] += 1
                continue
            if (row['date'] is None or row['date_inferred']
                    or row['date_source'] != 'transaction_date'):
                excluded['unreliable_date'] += 1
                continue
            if not row['description'].strip():
                excluded['empty_description'] += 1
                continue
            key = (row['description'], row['currency'], amount)
            group = groups.setdefault(key, {'dates': set(), 'rows': 0})
            group['dates'].add(row['date'])
            group['rows'] += 1
        candidates = []
        for (description, currency, amount), group in groups.items():
            dates = sorted(group['dates'])
            if len(dates) < 3:
                continue
            gaps = [(date.fromisoformat(b) - date.fromisoformat(a)).days
                    for a, b in zip(dates, dates[1:])]
            if any(gap < 25 or gap > 35 for gap in gaps):
                continue
            # Decimal equality ignores scale. Canonicalize within our own
            # context, never the caller's precision or rounding mode.
            magnitude = format(amount.copy_abs().normalize(), 'f')
            candidates.append({
                'description': description, 'currency': currency,
                'amount_magnitude': magnitude, 'status': 'booked',
                'distinct_dates': dates, 'interval_days': gaps,
                'distinct_date_count': len(dates),
                'supporting_input_rows': group['rows'],
                'cadence_candidate': 'monthly_25_to_35_days',
                'certainty': 'unverified_pattern',
                'reason': 'same_exact_description_currency_amount_three_dates_all_gaps_25_35',
            })
        candidates.sort(key=lambda item: (item['currency'], item['description'],
                                         item['amount_magnitude']))
    return {
        'candidates': candidates, 'input_rows': len(records),
        'excluded_rows_by_first_reason': excluded,
        'scope': 'supplied_rows_only', 'history_completeness': 'not_verified',
        'deduplication': 'not_performed',
        'same_date_rows': 'not_independent_recurrence_evidence',
        'merchant_identity': 'not_verified',
        'future_charge': 'not_predicted', 'obligation': 'not_determined',
    }
