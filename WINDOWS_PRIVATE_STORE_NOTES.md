# Windows protected store notes

Offline storage code, 20 November 2026. It has not read, created or stored any real bank key, authorization code or session. Test data is synthetic.

## What it is

`windows_private_store.py` stores small named values for the current Windows user, encrypted with DPAPI (`CryptProtectData`, current user, UI forbidden, never machine scope). Each name has its own entropy, so a blob copied to another name fails to decrypt. The name allowlist and size limits match the POSIX `private_store.py`. The module refuses non-Windows platforms. The POSIX store is unchanged and still refuses Windows.

Writes encrypt first, create an exclusive temporary file, flush and fsync it, then `os.replace` onto the final name. A failed write removes its temporary file. A failure after replacement may leave the new file visible: read back, do not retry blindly.

Rejected: relative, UNC and `\\?\` paths, `.`/`..` components, `.`, `..` and empty components in the raw path text (checked before pathlib normalizes them), symlinks and junctions (reparse points) in any path component, hardlinked or non-regular files, empty or oversized files, tampered or wrong-name blobs.

Every operation revalidates all path components, so a symlink or junction swapped into an ancestor after construction is rejected on the next call. This is not atomic with the file operation: a swap between the check and the read or write is not prevented. The directory tree is assumed trusted and not mutated concurrently by a hostile process.

## What is verified, and where

- Linux, Python 3.10: `test_windows_private_store` 22 tests pass, no skips. The Windows-native suite has not been run on Windows.
- Logic tests run on any OS with a fake backend. They are not DPAPI evidence.
- `test_windows_native_store.py` defines its tests only when `os.name == 'nt'` (no skips anywhere). This PR adds no workflow, so nothing in it runs them. Real DPAPI evidence requires a native Windows run of `python -m unittest -v test_windows_private_store test_windows_native_store` and a green result on the head SHA. Even then it is a GitHub runner, not the owner's laptop or Windows version. The logic suite has not yet been run on Windows either.

## Not claimed

- No ACL inspection or repair. The directory is created with inherited permissions. DPAPI binds the data to the Windows user, but the file permissions themselves are not verified by this module.
- Not protected against processes running as the same user, against anyone with the user's Windows logon secret, or against a roaming-profile or backup restore to another account setup.
- Python memory is not zeroized. Backup behaviour of the chosen directory is not reviewed.
- No connection to the callback relay, signer or bank workflow. No locking: serialize writers above this module.
- Not tested on the owner's Windows version.
