# SPDX-License-Identifier: MIT
# Adapted from HALCONDEORO/tesco-ie-grocery-mcp src/doctor.mjs.
# Copyright (c) 2026 Marco Tevar
# Modifications Copyright (c) 2026 Marco Antonio Tevar Asensio
# See THIRD_PARTY_NOTICES.md and LICENSES/.
"""Opt-in read-only injected probe. No network client, config/key reads or CLI.

A diagnostic is not bank linking, consent renewal or a permission grant. This
helper never retries and never passes provider bodies/exceptions to its output.
"""
import asyncio
from dataclasses import dataclass
from async_boundary import _await_owned
from provider_pager import FetchStopped

@dataclass(frozen=True,repr=False)
class ProbeResult:
    status: int
    def __repr__(self):return '<ProbeResult private>'

_VERDICTS={
 'reachable': 'A read-only probe succeeded. This does not verify all accounts or complete history.',
 'reconnect_required': 'Provider authentication or consent must be checked by the account owner.',
 'access_denied': 'Provider refused this probe. Do not infer the exact reason or retry automatically.',
 'rate_limited': 'Provider rate-limited this probe. Stop; no automatic retry was made.',
 'provider_unavailable': 'Provider returned a temporary failure. No automatic retry was made.',
 'redirect_refused': 'Provider redirected this probe. The redirect was not followed.',
 'unexpected_response': 'Probe did not return the expected status. No private response was exposed.',
 'timeout': 'Probe exceeded the cooperative time budget. No automatic retry was made.',
 'probe_failed': 'Probe failed. No private exception or response was exposed.',
}

def _verdict(status):
    return {'status':status,'summary':_VERDICTS[status],
            'scope':'one_injected_read_probe','full_readiness_verified':False,
            'history_completeness':'unknown','automatic_retry':False}

async def run_doctor(probe,*,seconds=3.0):
    """Call exactly once, only when the operator explicitly invokes this helper.

    The caller must supply an already-authorized fixed-path read-only probe.
    This function cannot verify the injected callable's behavior. Do not wire it
    to MCP or to an automatic startup health check for a real banking account.
    """
    if type(seconds) not in {int,float} or not 0<seconds<=5 or not callable(probe):
        raise ValueError('Invalid diagnostic configuration') from None
    loop=asyncio.get_running_loop();deadline=loop.time()+seconds
    try:
        result=await _await_owned(probe(),seconds)
        if loop.time()>=deadline:return _verdict('timeout')
        if type(result) is not ProbeResult or type(result.status) is not int:
            return _verdict('unexpected_response')
        code=result.status
        if code==200:key='reachable'
        elif code==401:key='reconnect_required'
        elif code==403:key='access_denied'
        elif code==429:key='rate_limited'
        elif code in {500,502,503,504}:key='provider_unavailable'
        elif 300<=code<400:key='redirect_refused'
        else:key='unexpected_response'
        return _verdict(key)
    except asyncio.TimeoutError:return _verdict('timeout')
    except FetchStopped as error:
        # Known fixed transport codes only; never echo unknown str(error).
        return _verdict('timeout' if error.args==('time_budget',) else 'probe_failed')
    except Exception:return _verdict('probe_failed')
