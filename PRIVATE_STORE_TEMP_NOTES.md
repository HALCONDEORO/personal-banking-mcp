# Exclusive temporary-file custody

Base de790588c7203daa7e16e22208910e3e68947604. Independent synthetic audit reproduced a low-severity cleanup defect: when os.open(O_EXCL) refused an existing random temporary name, finally removed that preexisting file even though this write never created it.

The cleanup-owned name is now assigned only after exclusive open succeeds. A collision is refused without unlinking the other entry. Existing write/fsync/replace ordering and generic errors are unchanged. Same-UID hostile concurrent processes remain outside the store's documented boundary; this is not new multi-process locking or full identity-retention protection.

4 new methods cover regular-file/symlink/FIFO/directory collisions, cleanup of owned temporaries on fchmod/write/fsync/replace failures, and postcommit directory-fsync uncertainty with target preserved. 381 Python tests normal/-O, Node9/55/58 seed381 pass. No credentials, banking network, Windows claim or host execution.
