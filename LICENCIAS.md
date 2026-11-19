# Dependency and source licenses

The synthetic server and `requirements.txt` are included in this repository. Installed dependency inventories are in `dependency-licenses.json` and `node-dependency-licenses.json`. The project is not dependency-free.

Original code is MIT, copyright 2026 Marco Antonio Tevar Asensio. File-specific third-party exceptions and adapted sources are documented in `THIRD_PARTY_NOTICES.md`; for example, `admin_consent.py` remains Apache-2.0. Full license texts are retained in `LICENSE` and `LICENSES/`. Do not infer that the root MIT license relicenses every file or installed package.

The official MCP Python SDK is an installed MIT dependency, not vendored source. Its notice is preserved in `THIRD_PARTY_NOTICES.md`. Other installed packages retain their own licenses. Inventory metadata does not replace their license texts or redistribution obligations.

Versions are pinned in `requirements.txt`, but that file is not an artifact-hash lockfile. JavaScript dependencies use the npm lockfile. Every dependency change requires a fresh license/compatibility review and preservation of applicable notices. Do not copy third-party source without tracing provenance and retaining its obligations.

Code licensing does not grant access to provider APIs, rights to bank data, trademark rights or regulatory permission. See `TERMS.md` for the separation between this software and provider conditions.
