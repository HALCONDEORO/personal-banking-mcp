# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Separate explicitly invoked AIS setup POST transport. Never an MCP tool.

This module creates/authorizes provider AIS sessions when invoked with real
credentials. Its existence does not grant authority to run it. No payments,
DELETE, general URL/method API, config/key reads, logging or retry.
"""
import asyncio,json,re,time
import httpx
from urllib.parse import urlsplit,parse_qsl
from provider_http import suppress_provider_diagnostics, _await_request
from provider_pager import _strict_response_json

HOST='https://api.enablebanking.com'
MAX_BYTES=131072
class AdminStopped(ValueError):pass

def stop():raise AdminStopped('Admin setup request stopped') from None

class PrivateReply:
    __slots__=('_data',)
    def __init__(self,data):self._data=data
    def __repr__(self):return '<PrivateReply private>'
    def take(self):
        if self._data is None:stop()
        data=self._data;self._data=None;return data


def _auth_body(body):
    from provider_session import _time
    if type(body) is not dict or set(body)!={'access','aspsp','state','redirect_url','psu_type'}:stop()
    if body['psu_type']!='personal' or body['redirect_url']!='https://localhost:8765/callback':stop()
    if type(body['state']) is not str or re.fullmatch(r'[A-Za-z0-9_-]{43}',body['state']) is None:stop()
    access=body['access'];bank=body['aspsp']
    if type(access) is not dict or set(access)!={'valid_until'} or type(bank) is not dict or set(bank)!={'name','country'}:stop()
    if (type(bank['name']) is not str or not 1<=len(bank['name'])<=120
            or any(ord(c)<32 for c in bank['name']) or type(bank['country']) is not str
            or re.fullmatch(r'[A-Z]{2}',bank['country']) is None):stop()
    value=access['valid_until']
    if type(value) is not str or not 20<=len(value)<=40:stop()
    try:
        _time(value)
    except (ValueError,OverflowError):stop()
    # Builder owns approved duration/current time. No extension is introduced.


def _code_body(body):
    if type(body) is not dict or set(body)!={'code'}:stop()
    value=body['code']
    if type(value) is not str or not 1<=len(value)<=4096 or any(ord(c)<33 or ord(c)>126 for c in value):stop()


def _auth_reply(data):
    # Only official first-party AIS start URL is supported initially. A future
    # provider URL shape change must be reviewed, never arbitrary-host fallback.
    if type(data) is not dict or type(data.get('url')) is not str or len(data['url'])>4096:stop()
    try:
        p=urlsplit(data['url'])
        if (p.scheme!='https' or p.netloc!='auth.enablebanking.com' or p.path!='/ais/start'
                or p.fragment or any(ord(c)<33 or ord(c)>126 for c in data['url'])):stop()
        pairs=parse_qsl(p.query,strict_parsing=True,max_num_fields=8,errors='strict')
        if len(pairs)!=1 or pairs[0][0]!='sessionid':stop()
        from uuid import UUID
        if str(UUID(pairs[0][1]))!=pairs[0][1]:stop()
    except (ValueError,UnicodeError):stop()
    # URL remains private, displayed only in the owner's explicit admin flow.
    return {'url':data['url']}

class AdminAISHTTP:
    """One POST per call; no ambiguous-failure retry. Constructing has no I/O.

    Owner must authorize each workflow. Use ConsentAttempt bodies and consume
    callbacks before exchange. Never wire these methods to read-only MCP tools.
    """
    def __init__(self,token,*,total_seconds=5.0,_test_transport=None):
        if not callable(token) or type(total_seconds) not in {int,float} or not 0<total_seconds<=5:stop()
        self._token=token;self._seconds=total_seconds;self._transport=_test_transport
    def __repr__(self):return '<AdminAISHTTP private>'
    async def start_authorization(self,body):
        _auth_body(body)
        data=await self._post('/auth',body)
        return PrivateReply(_auth_reply(data))
    async def exchange_code(self,body):
        _code_body(body)
        # Caller MUST run validate_created_session with its expected bank,
        # country/duration before storing/wiring IDs; raw reply stays private.
        return PrivateReply(await self._post('/sessions',body))
    async def _post(self,path,body):
        # Also guard the private method against accidental widening.
        if path=='/auth':_auth_body(body)
        elif path=='/sessions':_code_body(body)
        else:stop()
        deadline=time.monotonic()+self._seconds
        try:
            result=await _await_request(self._request(path,body,deadline),self._seconds)
            if time.monotonic()>=deadline:stop()
            return result
        except Exception:stop()
    async def _request(self,path,body,deadline):
        def check():
            if time.monotonic()>=deadline:stop()
        try:
            content=json.dumps(body,separators=(',',':'),ensure_ascii=True).encode('ascii')
            if len(content)>8192:stop()
            token=self._token();check()
            if type(token) is not str or len(token)>16384 or re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',token) is None:stop()
            suppress_provider_diagnostics()
            async with httpx.AsyncClient(transport=self._transport,trust_env=False,follow_redirects=False,
                    timeout=httpx.Timeout(5,connect=3),limits=httpx.Limits(max_connections=1,max_keepalive_connections=0)) as client:
                async with client.stream('POST',HOST+path,content=content,headers={
                    'Authorization':'Bearer '+token,'Accept':'application/json','Accept-Encoding':'identity',
                    'Content-Type':'application/json'}) as response:
                    check()
                    if response.status_code!=200:stop() # no private error body read
                    if response.headers.get('content-encoding','identity').strip().lower()!='identity':stop()
                    if response.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':stop()
                    length=response.headers.get('content-length')
                    if length is not None and (not length.isascii() or not length.isdigit() or int(length)>MAX_BYTES):stop()
                    data=bytearray()
                    async for chunk in response.aiter_raw(chunk_size=8192):
                        check()
                        if len(data)+len(chunk)>MAX_BYTES:stop()
                        data.extend(chunk)
                    check()
                    result=_strict_response_json(data)
                    if type(result) is not dict:stop()
                    return result
        except Exception:stop()
