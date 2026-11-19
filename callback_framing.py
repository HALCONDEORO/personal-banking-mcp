# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Bounded private backend HTTP parser. No sockets, TLS, logs or bank requests.

This parser handles the plaintext loopback request REBUILT by the reviewed TLS
relay, not arbitrary browser HTTP. TLS relay and socket lifecycle are separate
release gates. The relay uses a fixed Host and strips all browser headers.
"""
import re

class CallbackRejected(ValueError):pass

def reject():raise CallbackRejected('Callback request rejected') from None

MAX_REQUEST=12288
MAX_TARGET=8192
BACKEND_HOST='127.0.0.1:8766'
ORIGIN='https://localhost:8765'


def parse_relay_request(raw: bytes) -> str:
    """Return a PRIVATE callback URL for ConsentAttempt.consume_callback.

    Only a dedicated loopback-only listener behind the owner's authenticated
    SSH tunnel may call this parser. HTTP Host is not authentication.
    """
    if type(raw) is not bytes or not 1<=len(raw)<=MAX_REQUEST:reject()
    if not raw.endswith(b'\r\n\r\n') or b'\r\n\r\n' in raw[:-4]:reject()
    try:text=raw.decode('ascii')
    except UnicodeError:reject()
    lines=text[:-4].split('\r\n')
    if len(lines)!=3:reject()
    line=lines[0]
    if any(ord(c)<32 or ord(c)>126 for c in line):reject()
    parts=line.split(' ')
    if len(parts)!=3 or parts[0]!='GET' or parts[2]!='HTTP/1.1':reject()
    target=parts[1]
    if (not 1<=len(target)<=MAX_TARGET or not target.startswith('/callback?')
            or '#' in target or '\\' in target
            or re.search(r'%(?![0-9a-fA-F]{2})',target)):
        reject()
    # Fixed relay protocol: exactly Host and Connection: close, in this order.
    # No Content-Length, Transfer-Encoding, forwarding headers, cookies or auth.
    if lines[1]!='Host: '+BACKEND_HOST or lines[2]!='Connection: close':reject()
    return ORIGIN+target


def relay_request(target: str) -> bytes:
    """Build the ONLY request shape emitted by a future TLS relay.

    Do not supply an absolute URL or a target derived from an arbitrary Host.
    Browser-facing parsing remains a separate task, not implemented here.
    """
    if type(target) is not str:reject()
    try:raw=('GET '+target+' HTTP/1.1\r\nHost: '+BACKEND_HOST+'\r\nConnection: close\r\n\r\n').encode('ascii')
    except UnicodeError:reject()
    parse_relay_request(raw)
    return raw


def response_bytes(*,accepted: bool) -> bytes:
    """Constant no-store text, never reflect URL, provider text, state or code.

    Accepted means callback validated locally, not a created bank session.
    """
    if type(accepted) is not bool:reject()
    status='200 OK' if accepted else '400 Bad Request'
    body=(b'Callback validated locally. Bank session is not confirmed.\n' if accepted
          else b'Callback not accepted. Close this window and restart setup if needed.\n')
    headers=('HTTP/1.1 '+status+'\r\nContent-Type: text/plain; charset=utf-8\r\n'
             'Cache-Control: no-store\r\nReferrer-Policy: no-referrer\r\n'
             "Content-Security-Policy: default-src 'none'; frame-ancestors 'none'\r\n"
             'X-Content-Type-Options: nosniff\r\nConnection: close\r\n'
             'Content-Length: '+str(len(body))+'\r\n\r\n').encode('ascii')
    return headers+body
