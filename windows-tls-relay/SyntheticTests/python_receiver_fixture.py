# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Private PIPE-only synthetic join fixture. Never import or run real setup."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from admin_consent import ConsentAttempt
from callback_receiver import CallbackReceiver, ReceiverStopped


async def main():
    attempt = ConsentAttempt('https://localhost:8765/callback')
    body = attempt.authorization_body('Synthetic bank', 'IE', now=datetime.now(timezone.utc))
    receiver = CallbackReceiver(attempt, port=0, lifetime_seconds=10)
    try:
        await receiver.start()
        # Ephemeral synthetic state only; parent consumes this pipe, never prints it.
        denial = sys.argv[1:] == ['denial']
        fields = {'state': body['state']}
        fields.update({'error': 'synthetic_denial'} if denial else {'code': 'SYNTHETIC-JOIN-CODE'})
        print(json.dumps({'port': receiver.port, 'target': '/callback?' + urlencode(fields)}), flush=True)
        try:
            result = await asyncio.wait_for(receiver.wait_private_result(), 10)
        except ReceiverStopped:
            return 0 if denial and attempt.closed else 1
        if denial:
            return 1
        if result != {'code': 'SYNTHETIC-JOIN-CODE'}:
            return 1
        return 0
    finally:
        await receiver.close()


if __name__ == '__main__':
    try:
        status = asyncio.run(main())
    except BaseException:
        status = 1
    raise SystemExit(status)
