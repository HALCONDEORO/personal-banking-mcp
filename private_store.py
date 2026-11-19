# SPDX-License-Identifier: MIT
# Adapted from Studio-Saelix/finance-mcp src/plaid_mcp/paths.py.
# Copyright (c) 2026 plaid-mcp contributors
# Modifications Copyright (c) 2026 Marco Antonio Tevar Asensio
# See LICENSES/Studio-Saelix-MIT.txt and THIRD_PARTY_NOTICES.md.
"""POSIX-only owner-private, descriptor-relative storage. No secret logging.

Local same-UID hostile processes are outside this boundary. No repository paths
or XDG defaults are chosen here. The admin selects an isolated absolute directory.
Existing insecure permissions are rejected, never silently repaired.
"""
from __future__ import annotations
import contextlib
import os
import re
import secrets
import stat
from pathlib import Path

MAX_BYTES = 131072

class PrivateStoreError(ValueError):
    pass

def reject():
    raise PrivateStoreError('Private storage rejected') from None

def _name(name):
    if type(name) is not str or re.fullmatch(r'[a-z][a-z0-9_-]{0,63}\.(?:pem|json)', name) is None:
        reject()
    return name

def _private(info, directory=False):
    want = 0o700 if directory else 0o600
    if (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != want
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or (not directory and info.st_nlink != 1)):
        reject()

class PrivateStore:
    """Call .close() or use as context manager. Never use objects after close."""
    def __init__(self, path: str | Path):
        self._fd = -1
        fd = -1
        try:
            if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
                reject()
            raw = os.fspath(path)
            if type(raw) is not str or not raw.startswith('/') or raw == '/' or '\x00' in raw:
                reject()
            parts = raw.split('/')[1:]
            if any(p in ('', '.', '..') for p in parts):
                reject()
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            fd = os.open('/', flags)
            for i, component in enumerate(parts):
                if i == len(parts)-1:
                    try:os.mkdir(component, 0o700, dir_fd=fd)
                    except FileExistsError:pass
                nxt = os.open(component, flags, dir_fd=fd)
                os.close(fd)
                fd = nxt
            _private(os.fstat(fd), directory=True)
            self._fd, fd = fd, -1
        except (OSError, TypeError, ValueError):
            reject()
        finally:
            if fd >= 0:os.close(fd)

    def __repr__(self):return '<PrivateStore private>'
    def __enter__(self):return self
    def __exit__(self, *args):self.close()
    def close(self):
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1
    def _active(self):
        if self._fd < 0:reject()
        _private(os.fstat(self._fd), directory=True)

    def read(self, name: str) -> bytes:
        fd = -1
        try:
            self._active();_name(name)
            fd = os.open(name, os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK, dir_fd=self._fd)
            info = os.fstat(fd);_private(info)
            if not 1 <= info.st_size <= MAX_BYTES:reject()
            chunks=[];size=0
            while True:
                chunk=os.read(fd,min(65536,MAX_BYTES+1-size))
                if not chunk:break
                chunks.append(chunk);size+=len(chunk)
                if size>MAX_BYTES:reject()
            if not chunks:reject()
            return b''.join(chunks)
        except (OSError, TypeError, ValueError):reject()
        finally:
            if fd>=0:os.close(fd)

    def write(self, name: str, data: bytes):
        """Atomic replacement, fsync file then directory. No temp names returned.

        If final directory fsync fails after replacement, an error is raised but
        the replacement may already be visible. Caller must read back, not retry
        blindly. No provider write is performed here.
        """
        fd=-1;temp=None
        try:
            self._active();_name(name)
            if type(data) is not bytes or not 1<=len(data)<=MAX_BYTES:reject()
            try:
                info=os.stat(name,dir_fd=self._fd,follow_symlinks=False)
                _private(info)
            except FileNotFoundError:pass
            temp='.new-'+secrets.token_hex(16)
            fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=self._fd)
            # Honour restrictive umask without accepting group/world access.
            os.fchmod(fd,0o600);_private(os.fstat(fd))
            view=memoryview(data)
            while view:
                n=os.write(fd,view)
                if n<=0:reject()
                view=view[n:]
            os.fsync(fd);os.close(fd);fd=-1
            os.replace(temp,name,src_dir_fd=self._fd,dst_dir_fd=self._fd)
            temp=None
            os.fsync(self._fd)
        except (OSError, TypeError, ValueError):reject()
        finally:
            if fd>=0:os.close(fd)
            if temp:
                with contextlib.suppress(OSError):os.unlink(temp,dir_fd=self._fd)
