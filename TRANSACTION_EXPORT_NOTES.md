# Explicit local transaction CSV prototype

Pure construction only. `build_transaction_csv(records, fields=[...])` returns UTF8-BOM bytes and scope metadata to a trusted caller. No file write, destination choice, share, upload, email, network, persistent cache or MCP tool is added. A future save/share requires its own owner-approved destination/audience and normal file checks. This package is not permission to export real account data.

The caller explicitly selects one to ten unique fields from normalized date/provenance, amount, currency, status, description and optional supplied category labels. There is no default column selection and no arbitrary provider/account/IBAN field. All input records are fully validated by the already reviewed transaction_analytics._rows boundary even if only one field is selected. Existing analytics source is a dependency, not a file to overwrite from this package.

At most1000supplied rows and1MiB encoded CSV, including BOM, headers and quoting. Exact input row order is retained. Missing optional dates/categories become empty cells, not guesses. No deduplication or complete-history claim. Pending-to-booked equivalence remains unknown; the caller chooses a known non-overlapping selection. CSV content remains private even after formula neutralization.

## Spreadsheet semantics

Uses stdlib CSV quoting and CRLF with a UTF8 BOM. Potentially executable cells get a leading apostrophe, including markers after ASCII whitespace or BOM; initial tab/CR/LF is also prefixed. This is a conservative defence adapted from upstream, not a guarantee for every spreadsheet/import configuration. It does not strip or execute original text and does not change the input records.

Amounts are deliberately formula-neutralized text, not spreadsheet numbers. For example -12.40 exports with a leading apostrophe. This protects the same conservative cell boundary and preserves exact displayed decimal characters, but a consumer that needs numeric calculations must use a separately reviewed import schema. Do not strip the prefix indiscriminately or claim this export is a lossless machine-roundtrip of original cells. The metadata says amount_encoding formula_neutralized_text and spreadsheet_safety defence_not_guarantee.

Never claim quotes alone prevent CSV injection. Re-saving/reinterpreting a CSV or choosing an unsafe spreadsheet import can defeat a text prefix. Review the consuming spreadsheet before real deployment. A UTF8 encoding failure, invalid selected field, invalid record or byte-cap failure returns only a generic refusal, not private data or a partial file.

## Provenance and licenses

Adapted `csv_cell` from chemical_cabinet/app.py at HALCONDEORO/chemical-cabinet pin a0ca143f206f7d92aa9b2676de00e729c282442e, MIT, Copyright(c)2026 chemical-cabinet contributors.
Pinned source:
https://raw.githubusercontent.com/HALCONDEORO/chemical-cabinet/a0ca143f206f7d92aa9b2676de00e729c282442e/chemical_cabinet/app.py
Full MIT text: LICENSES/chemical-cabinet-MIT.txt.
Changes: pure bounded financial normalized-row bytes construction, explicit field selection, no app/DB/path/write/share, scope metadata and tests. Before PR append a specific cumulative notice to THIRD_PARTY_NOTICES.md without replacing existing notices or licenses.

## Tests and limits

16 synthetic tests pass normal and optimized Python. Cover field subset/order, header-only output, BOM/CRLF, formula prefixes/controls, Unicode/quotes/newlines, safe-text retention, invalid/duplicate/private field refusal, generic validation, byte-cap with multibyte text, full-input validation, missing optional fields, no mutation, partial scope and invalid UTF8 surrogate. These tests are not an actual Excel/LibreOffice/Windows render or a universal spreadsheet safety proof. No real data is exported and no file delivery is performed.
