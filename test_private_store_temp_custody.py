"""Offline synthetic tempfile custody, no credentials or provider."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from private_store import PrivateStore,PrivateStoreError

TOKEN='1'*32

class TempCustodyTests(unittest.TestCase):
    def test_collision_preserves_existing_regular_file(self):
        with tempfile.TemporaryDirectory() as root,PrivateStore(Path(root)/'private') as store:
            other=Path(root)/'private'/('.new-'+TOKEN);other.write_bytes(b'SYNTHETIC-OTHER-WRITER');other.chmod(0o600)
            before=other.stat()
            with patch('private_store.secrets.token_hex',return_value=TOKEN):
                with self.assertRaises(PrivateStoreError):store.write('session.json',b'SYNTHETIC-NEW')
            self.assertEqual(other.read_bytes(),b'SYNTHETIC-OTHER-WRITER');self.assertEqual(other.stat().st_ino,before.st_ino)
            self.assertFalse((other.parent/'session.json').exists())
    def test_collision_preserves_symlink_fifo_and_directory(self):
        for kind in ('symlink','fifo','directory'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as root,PrivateStore(Path(root)/'private') as store:
                other=Path(root)/'private'/('.new-'+TOKEN);target=Path(root)/'target';target.write_bytes(b'SYNTHETIC-TARGET')
                if kind=='symlink':other.symlink_to(target)
                elif kind=='fifo':os.mkfifo(other,0o600)
                else:other.mkdir(mode=0o700)
                before=other.lstat()
                with patch('private_store.secrets.token_hex',return_value=TOKEN):
                    with self.assertRaises(PrivateStoreError):store.write('session.json',b'SYNTHETIC-NEW')
                self.assertEqual(other.lstat().st_ino,before.st_ino);self.assertEqual(target.read_bytes(),b'SYNTHETIC-TARGET')
    def test_owned_temp_removed_on_precommit_failures(self):
        for target in ('os.fchmod','os.write','os.fsync','os.replace'):
            with self.subTest(target=target),tempfile.TemporaryDirectory() as root,PrivateStore(Path(root)/'private') as store:
                store.write('key.pem',b'SYNTHETIC-OLD')
                with patch('private_store.'+target,side_effect=OSError()):
                    with self.assertRaises(PrivateStoreError):store.write('key.pem',b'SYNTHETIC-NEW')
                self.assertEqual(store.read('key.pem'),b'SYNTHETIC-OLD')
                self.assertEqual(sorted(p.name for p in (Path(root)/'private').iterdir()),['key.pem'])
    def test_postcommit_directory_fsync_uncertainty_does_not_remove_target(self):
        with tempfile.TemporaryDirectory() as root,PrivateStore(Path(root)/'private') as store:
            store.write('session.json',b'SYNTHETIC-OLD');real=os.fsync;calls=0
            def fsync(fd):
                nonlocal calls
                calls+=1
                if calls==2:raise OSError()
                return real(fd)
            with patch('private_store.os.fsync',side_effect=fsync):
                with self.assertRaises(PrivateStoreError):store.write('session.json',b'SYNTHETIC-NEW')
            self.assertEqual(store.read('session.json'),b'SYNTHETIC-NEW')
            self.assertEqual(sorted(p.name for p in (Path(root)/'private').iterdir()),['session.json'])

if __name__=='__main__':unittest.main()
