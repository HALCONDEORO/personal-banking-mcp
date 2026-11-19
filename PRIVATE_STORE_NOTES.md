# Private store integration notes

This module is offline storage code, not an authorization flow, vault integration or deployed service. It has not read, created or stored any real bank key, authorization code or session. Test strings are synthetic and do not authenticate anywhere.

## Boundary

POSIX only. Use a dedicated service UID and an operator-selected absolute directory outside the repository. The final directory must be exactly mode0700 and owned by that UID. Each file must be a regular file, mode0600, owned by that UID and have one hardlink. Existing insecure permissions cause a generic error; they are not silently repaired.

Every path component is opened with O_DIRECTORY/O_NOFOLLOW. Reads and writes are relative to the pinned final directory descriptor. A symlink in any component is rejected. Names are a strict small allowlist shape, no arbitrary paths. No repository, home, XDG or environment-derived default is chosen. Parent directories must exist; only the final private directory can be created.

Reads are capped at128KiB. Writes use owner-only exclusive temporary files, handle partial writes, fsync the temporary file, atomically replace the destination and fsync the directory. A failed pre-replacement write removes its temporary file. A failure after replacement but before successful directory fsync is an indeterminate durability outcome: the new file may already be visible. Read back to reconcile; do not blindly retry a higher-level operation.

The store neither parses nor validates PEM/JSON. Callers must validate schema/key properties before use and must not log returned bytes or repr their containing objects. Generic exceptions suppress ordinary exception chaining, but callers must not enable debugger/traceback options that capture local variables. Bytes may remain in Python memory and OS caches; no reliable zeroization claim is made.

Not protected against root, hostile processes sharing the same UID, disk theft, host compromise or a malicious filesystem. Use ordinary host isolation and encrypted storage where required. No locking or compare-and-swap version control: serialize setup/session writers above this module. Atomic replacement prevents partial-file reads, not lost updates by competing legitimate writers. This is not a database or a secret manager.

## Tests

Run `python -m unittest -v test_private_store` and `python -O -m unittest -v test_private_store` on a POSIX development host. Tests use only temporary directories and synthetic bytes. Cover owner permissions, replacement, traversal/symlinks, hardlinks, FIFO rejection without blocking, strict names, size/type bounds, missing files, failed replacement cleanup, partial writes and closed handles. They do not establish the security of a particular production host.

Creation durability limit: when this module creates the final private directory, its parent directory is not fsynced. Creation surviving a crash is not guaranteed. This is separate from fsync of file replacements inside an already existing private directory.
