# SPDX-License-Identifier: MIT
# Interface shape adapted from noskillish/bankmcp src/enablebanking.ts.
# Copyright (c) 2026 Nils Smed
# Modifications Copyright (c) 2026 Marco Antonio Tevar Asensio
# See THIRD_PARTY_NOTICES.md and LICENSES/bankmcp-MIT.txt.
"""Offline validation between private setup response and read-only transport.

No networking, session creation or selection of accounts by default. Private IDs
remain private, returned only through explicit admin accessors. Not an MCP tool.
"""
from __future__ import annotations
from datetime import datetime,timezone
import re
import uuid

class SessionRejected(ValueError):pass

def reject():raise SessionRejected('Session validation rejected') from None

def _uuid(value):
    try:
        if type(value) is not str or str(uuid.UUID(value))!=value or uuid.UUID(value).int==0:reject()
    except (ValueError,AttributeError):reject()
    return value

def _time(value):
    if (type(value) is not str or len(value)>40
            or re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})',value) is None):reject()
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        if result.tzinfo is None or result.utcoffset() is None:reject()
        return result.astimezone(timezone.utc)
    except (ValueError,OverflowError):reject()

def _now(value):
    if not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset() is None:reject()
    return value.astimezone(timezone.utc)

class PrivateSession:
    """Sanitized private envelope, never serialize through repr/asdict.

    The caller must check live provider session status before real reads. Local
    expiry is only a fail-closed limit, never proof that consent remains active.
    """
    __slots__=('_id','_accounts','_until')
    def __init__(self, session_id,accounts,until):
        # Constructor is private-by-convention, validate all public inputs too.
        self._id=_uuid(session_id)
        if type(accounts) is not tuple or not 1<=len(accounts)<=50:reject()
        self._accounts=tuple(_uuid(x) for x in accounts)
        if len(set(self._accounts))!=len(self._accounts):reject()
        self._until=_now(until)
    def __repr__(self):return '<PrivateSession private>'
    def require_active(self,*,now):
        if _now(now)>=self._until:reject()
    def transport_ids(self,*,now):
        """Private internal handoff only. Never log/return these IDs to MCP."""
        self.require_active(now=now)
        return self._id,self._accounts
    def summary(self,*,now):
        self.require_active(now=now)
        return {'account_count':len(self._accounts),'valid_until':self._until.isoformat(),
                'live_consent_status':'not_verified','readiness':'local_validation_only'}


def validate_created_session(payload, *, selected_bank, selected_country,
                             requested_until, now) -> PrivateSession:
    """Keep only explicit allowlisted IDs and expiry from POST/sessions.

    Bank/country/requested_until come from the owner's current approved attempt,
    not from the response being validated. UUID shape does not prove ownership.
    """
    current=_now(now);requested=_now(requested_until)
    if (type(selected_bank) is not str or not 1<=len(selected_bank)<=120
            or any(ord(c)<32 for c in selected_bank)
            or type(selected_country) is not str or re.fullmatch(r'[A-Z]{2}',selected_country) is None
            or requested<=current or not isinstance(payload,dict)):
        reject()
    if (payload.get('psu_type')!='personal' or not isinstance(payload.get('aspsp'),dict)
            or payload['aspsp'].get('name')!=selected_bank
            or payload['aspsp'].get('country')!=selected_country
            or not isinstance(payload.get('access'),dict)):
        reject()
    until=_time(payload['access'].get('valid_until'))
    if not current<until<=requested:reject()
    accounts=payload.get('accounts')
    if type(accounts) is not list or not 1<=len(accounts)<=50:reject()
    ids=[]
    for item in accounts:
        if not isinstance(item,dict):reject()
        ids.append(_uuid(item.get('uid')))
    if len(set(ids))!=len(ids):reject()
    return PrivateSession(_uuid(payload.get('session_id')),tuple(ids),until)
