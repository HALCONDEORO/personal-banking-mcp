# Windows protected store notes

Offline storage code, 20 November 2026. It has not read, created or stored any real bank key, authorization code or session. Test data is synthetic.

## What it is

`windows_private_store.py` stores small named values for the current Windows user, encrypted with DPAPI (`CryptProtectData`, current user, UI forbidden, never machine scope). Each name has its own entropy, so a blob copied to another name fails to decrypt. The name allowlist and size limits match the POSIX `private_store.py`. The module refuses non-Windows platforms. The POSIX store is unchanged and still refuses Windows.

Writes encrypt first, create an exclusive temporary file, flush and fsync it, then `os.replace` onto the final name. A failed write removes its temporary file. A failure after replacement may leave the new file visible: read back, do not retry blindly.

Rejected: relative, UNC and `\\?\` paths, `.`/`..` components, symlinks and junctions (reparse points) in any path component, hardlinked or non-regular files, empty or oversized files, tampered or wrong-name blobs.

## What is verified, and where

- Logic tests run on any OS with a fake backend. They are not DPAPI evidence.
- `RealDpapi` tests are skipped unless `os.name == 'nt'`. This PR adds no workflow, so nothing in it runs them. Real DPAPI evidence requires a native Windows run of `python -m unittest -v test_windows_private_store`, for example from the separate Windows CI job once it exists, and a green result on the head SHA. Even then it is a GitHub runner, not the owner's laptop or Windows version.

## Not claimed

- No ACL inspection or repair. The directory is created with inherited permissions. DPAPI binds the data to the Windows user, but the file permissions themselves are not verified by this module.
- Not protected against processes running as the same user, against anyone with the user's Windows logon secret, or against a roaming-profile or backup restore to another account setup.
- Python memory is not zeroized. Backup behaviour of the chosen directory is not reviewed.
- No connection to the callback relay, signer or bank workflow. No locking: serialize writers above this module.
- Not tested on the owner's Windows version.
