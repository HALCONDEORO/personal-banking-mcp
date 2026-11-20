# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Windows-native protected storage using DPAPI (current user). No secret logging.

Each value is encrypted with CryptProtectData for the current Windows user,
with a per-name entropy so a blob copied under another name is rejected. The
admin selects an absolute directory outside the repository. Files hold only
DPAPI blobs. Same-user hostile processes can call DPAPI as that user and are
outside this boundary, as is anything with the user's logon secret.

This module refuses non-Windows platforms. Linux unit tests inject a fake
backend and exercise logic only; they say nothing about real DPAPI. Real
DPAPI is exercised only by tests that run on native Windows.
"""
from __future__ import annotations
import contextlib
import os
import re
import secrets
import stat
from pathlib import Path

MAX_BYTES = 131072
_BLOB_MAX = MAX_BYTES + 4096
_REPARSE = 0x400
_DOMAIN = b'personal-banking-mcp/windows-private-store/v1/'


class WindowsPrivateStoreError(ValueError):
    pass


def reject():
    raise WindowsPrivateStoreError('Private storage rejected') from None


def _name(name):
    if type(name) is not str or re.fullmatch(r'[a-z][a-z0-9_-]{0,63}\.(?:pem|json)', name) is None:
        reject()
    return name


class DpapiBackend:
    """Current-user DPAPI through ctypes. Only constructible on native Windows."""

    def __init__(self):
        if os.name != 'nt':
            reject()
        import ctypes
        from ctypes import wintypes

        class Blob(ctypes.Structure):
            _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

        self._ct, self._Blob = ctypes, Blob
        self._crypt = ctypes.WinDLL('crypt32', use_last_error=True)
        self._kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self._kernel.LocalFree.argtypes = [ctypes.c_void_p]
        self._kernel.LocalFree.restype = ctypes.c_void_p
        for fn in (self._crypt.CryptProtectData, self._crypt.CryptUnprotectData):
            fn.restype = wintypes.BOOL

    def _blob(self, data):
        buf = self._ct.create_string_buffer(data, len(data))
        return self._Blob(len(data), self._ct.cast(buf, self._ct.POINTER(self._ct.c_char))), buf

    def _run(self, fn, data, entropy):
        ct = self._ct
        src, keep1 = self._blob(data)
        ent, keep2 = self._blob(entropy)
        out = self._Blob()
        flags = 0x1  # CRYPTPROTECT_UI_FORBIDDEN; never LOCAL_MACHINE
        ok = fn(ct.byref(src), None, ct.byref(ent), None, None, flags, ct.byref(out))
        del keep1, keep2
        if not ok:
            reject()
        try:
            return ct.string_at(out.pbData, out.cbData)
        finally:
            ct.memset(out.pbData, 0, out.cbData)
            self._kernel.LocalFree(out.pbData)

    def protect(self, data, entropy):
        return self._run(self._crypt.CryptProtectData, data, entropy)

    def unprotect(self, blob, entropy):
        return self._run(self._crypt.CryptUnprotectData, blob, entropy)


def _plain_dir(path):
    """Reject reparse points, symlinks and non-directories for one component."""
    try:
        info = os.lstat(path)
    except OSError:
        reject()
    attrs = getattr(info, 'st_file_attributes', 0)
    if stat.S_ISLNK(info.st_mode) or attrs & _REPARSE or not stat.S_ISDIR(info.st_mode):
        reject()


class WindowsPrivateStore:
    """Use as a context manager. Backend injection is for synthetic tests only."""

    def __init__(self, path, *, _backend=None, _platform=None):
        self._root = None
        self._backend = None
        try:
            if (_platform or os.name) != 'nt':
                reject()
            raw = os.fspath(path)
            if type(raw) is not str or '\x00' in raw or not os.path.isabs(raw):
                reject()
            p = Path(raw)
            if not p.drive or p.drive.startswith('\\\\') or raw.startswith(('\\\\', '//')):
                reject()  # drive-letter absolute paths only; no UNC, no \\?\ forms
            parts = p.parts[1:]
            if not parts or any(c in ('', '.', '..') or ':' in c or c.endswith(('.', ' ')) for c in parts):
                reject()
            cur = Path(p.anchor)
            for i, comp in enumerate(parts):
                cur = cur / comp
                if i == len(parts) - 1 and not cur.exists():
                    os.mkdir(cur)
                _plain_dir(cur)
            self._root = cur
            self._backend = _backend if _backend is not None else DpapiBackend()
        except (OSError, TypeError, ValueError):
            reject()

    def __repr__(self):
        return '<WindowsPrivateStore private>'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._root = None
        self._backend = None

    def _active(self):
        if self._root is None:
            reject()
        _plain_dir(self._root)

    def _file(self, name):
        return self._root / _name(name)

    @staticmethod
    def _entropy(name):
        return _DOMAIN + name.encode('ascii')

    def read(self, name: str) -> bytes:
        try:
            self._active()
            path = self._file(name)
            info = os.lstat(path)
            attrs = getattr(info, 'st_file_attributes', 0)
            if (not stat.S_ISREG(info.st_mode) or attrs & _REPARSE or info.st_nlink != 1
                    or not 1 <= info.st_size <= _BLOB_MAX):
                reject()
            with open(path, 'rb') as fh:
                blob = fh.read(_BLOB_MAX + 1)
            if not 1 <= len(blob) <= _BLOB_MAX:
                reject()
            data = self._backend.unprotect(blob, self._entropy(name))
            if type(data) is not bytes or not 1 <= len(data) <= MAX_BYTES:
                reject()
            return data
        except (OSError, TypeError, ValueError):
            reject()

    def write(self, name: str, data: bytes):
        """Atomic replacement. After os.replace, a failure may leave the new file visible.

        Read back to reconcile; do not retry blindly.
        """
        temp = None
        try:
            self._active()
            final = self._file(name)
            if type(data) is not bytes or not 1 <= len(data) <= MAX_BYTES:
                reject()
            try:
                info = os.lstat(final)
                if (not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & _REPARSE
                        or info.st_nlink != 1):
                    reject()
            except FileNotFoundError:
                pass
            blob = self._backend.protect(data, self._entropy(name))
            if type(blob) is not bytes or not 1 <= len(blob) <= _BLOB_MAX:
                reject()
            candidate = self._root / ('.new-' + secrets.token_hex(16))
            with open(candidate, 'xb') as fh:
                temp = candidate  # exclusive creation succeeded; cleanup owns it
                fh.write(blob)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temp, final)
            temp = None
        except (OSError, TypeError, ValueError):
            reject()
        finally:
            if temp is not None:
                with contextlib.suppress(OSError):
                    os.unlink(temp)
