# SPDX-License-Identifier: MIT
# Adapted csv_cell pattern: HALCONDEORO/chemical-cabinet,
# a0ca143f206f7d92aa9b2676de00e729c282442e, MIT.
# Copyright (c) 2026 chemical-cabinet contributors
# Changes: explicit normalized financial field selection, bounded byte output,
# no web handler/path/database and no output side effect.
"""Pure, explicit CSV construction. Does not write, upload or expose an MCP tool."""
import csv
import io
from transaction_analytics import _rows


class ExportStopped(ValueError):
    def __init__(self):super().__init__('Local CSV export stopped')


_ALLOWED={'date','date_source','date_inferred','amount','currency','currency_known',
          'status','description','user_category','provider_category'}


def _cell(value):
    text='' if value is None else str(value)
    probe=text.lstrip(' \t\r\n\v\f\ufeff')
    if text[:1] in ('\t','\r','\n') or probe[:1] in ('=','+','-','@'):
        return "'"+text
    return text


def build_transaction_csv(records, *, fields):
    """Return bounded UTF8-BOM bytes and scope metadata, never a file/share.

    All cells are text exports. Prefixing negative amounts is intentional to
    preserve a conservative formula defence, not a numeric spreadsheet format.
    """
    if type(fields) is not list or not 1<=len(fields)<=10:
        raise ExportStopped()
    if any(type(field) is not str or field not in _ALLOWED for field in fields):
        raise ExportStopped()
    if len(set(fields))!=len(fields):raise ExportStopped()
    invalid=False
    try:validated=_rows(records)
    except ValueError:invalid=True
    if invalid:raise ExportStopped()
    parts=[b'\xef\xbb\xbf'];size=3
    def append(values):
        nonlocal size
        buf=io.StringIO(newline='');csv.writer(buf,lineterminator='\r\n').writerow(values)
        failed=False
        try:chunk=buf.getvalue().encode('utf-8')
        except UnicodeError:failed=True
        if failed:raise ExportStopped()
        size+=len(chunk)
        if size>1048576:raise ExportStopped()
        parts.append(chunk)
    append(fields)
    for record,_ in validated:
        append([_cell(record.get(field)) for field in fields])
    return {'csv_utf8_bytes':b''.join(parts), 'rows':len(validated),'fields':list(fields),
            'scope':'supplied_rows_only','history_completeness':'not_verified',
            'deduplication':'not_performed','amount_encoding':'formula_neutralized_text',
            'spreadsheet_safety':'defence_not_guarantee'}
