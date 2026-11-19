import os,stat,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from private_store import PrivateStore,PrivateStoreError,MAX_BYTES

class TestStore(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'private'
  self.store=PrivateStore(str(self.path))
 def tearDown(self):self.store.close();self.tmp.cleanup()
 def test_roundtrip(self):
  self.store.write('session.json',b'{"synthetic":true}');self.assertEqual(self.store.read('session.json'),b'{"synthetic":true}')
 def test_permissions(self):
  self.store.write('key.pem',b'synthetic key')
  self.assertEqual(stat.S_IMODE(self.path.stat().st_mode),0o700)
  self.assertEqual(stat.S_IMODE((self.path/'key.pem').stat().st_mode),0o600)
 def test_replace(self):
  self.store.write('session.json',b'one');ino=(self.path/'session.json').stat().st_ino
  self.store.write('session.json',b'two');self.assertNotEqual(ino,(self.path/'session.json').stat().st_ino)
  self.assertEqual(self.store.read('session.json'),b'two')
 def test_no_temps(self):
  self.store.write('key.pem',b'x');self.assertEqual([p.name for p in self.path.iterdir()],['key.pem'])
 def test_symlink_file(self):
  target=self.root/'target';target.write_bytes(b'private target');os.symlink(target,self.path/'key.pem')
  for action in [lambda:self.store.read('key.pem'),lambda:self.store.write('key.pem',b'evil')]:
   with self.assertRaises(PrivateStoreError):action()
  self.assertEqual(target.read_bytes(),b'private target')
 def test_symlink_directory(self):
  alias=self.root/'alias';os.symlink(self.path,alias)
  with self.assertRaises(PrivateStoreError):PrivateStore(str(alias))
 def test_ancestor_symlink(self):
  alias=self.root/'alias';os.symlink(self.root,alias)
  with self.assertRaises(PrivateStoreError):PrivateStore(str(alias/'newprivate'))
  self.assertFalse((self.root/'newprivate').exists())
 def test_insecure_directory(self):
  os.chmod(self.path,0o755)
  with self.assertRaises(PrivateStoreError):PrivateStore(str(self.path))
  with self.assertRaises(PrivateStoreError):self.store.write('key.pem',b'x')
 def test_insecure_file(self):
  self.store.write('key.pem',b'x');os.chmod(self.path/'key.pem',0o644)
  with self.assertRaises(PrivateStoreError):self.store.read('key.pem')
  with self.assertRaises(PrivateStoreError):self.store.write('key.pem',b'y')
 def test_hardlink(self):
  self.store.write('key.pem',b'x');os.link(self.path/'key.pem',self.path/'copy.pem')
  with self.assertRaises(PrivateStoreError):self.store.read('key.pem')
  with self.assertRaises(PrivateStoreError):self.store.write('key.pem',b'y')
 def test_fifo_no_block(self):
  os.mkfifo(self.path/'key.pem',0o600)
  with self.assertRaises(PrivateStoreError):self.store.read('key.pem')
 def test_name_allowlist(self):
  for name in ['../key.pem','/key.pem','x/y.pem','.key.pem','key.log','key.pem\n','UPPER.pem',True]:
   with self.subTest(name=name),self.assertRaises(PrivateStoreError):self.store.write(name,b'x')
 def test_bounds(self):
  for data in [b'',b'x'*(MAX_BYTES+1),'text',None]:
   with self.subTest(size=len(data) if data else 0),self.assertRaises(PrivateStoreError):self.store.write('key.pem',data)
  self.store.write('key.pem',b'x'*MAX_BYTES);self.assertEqual(len(self.store.read('key.pem')),MAX_BYTES)
 def test_oversized_read(self):
  p=self.path/'key.pem';p.write_bytes(b'x'*(MAX_BYTES+1));p.chmod(0o600)
  with self.assertRaises(PrivateStoreError):self.store.read('key.pem')
 def test_missing_generic(self):
  with self.assertRaises(PrivateStoreError) as e:self.store.read('key.pem')
  self.assertNotIn(str(self.path),str(e.exception));self.assertEqual(str(e.exception),'Private storage rejected')
 def test_failed_replace_cleanup(self):
  self.store.write('key.pem',b'old')
  with patch('private_store.os.replace',side_effect=OSError('synthetic private detail')):
   with self.assertRaises(PrivateStoreError) as e:self.store.write('key.pem',b'new')
  self.assertNotIn('detail',str(e.exception));self.assertEqual(self.store.read('key.pem'),b'old')
  self.assertEqual([p.name for p in self.path.iterdir()],['key.pem'])
 def test_partial_writes(self):
  real=os.write
  with patch('private_store.os.write',side_effect=lambda fd,b:real(fd,b[:3])):self.store.write('key.pem',b'abcdefghijk')
  self.assertEqual(self.store.read('key.pem'),b'abcdefghijk')
 def test_read_context(self):
  with PrivateStore(str(self.path)) as s:s.write('key.pem',b'x')
  with self.assertRaises(PrivateStoreError):s.read('key.pem')
 def test_close_idempotent(self):
  self.store.close();self.store.close()
  with self.assertRaises(PrivateStoreError):self.store.write('key.pem',b'x')
 def test_bad_paths(self):
  for path in ['/','relative',str(self.root)+'/../other',str(self.path)+'/',str(self.root)+'//new']:
   with self.subTest(path=path),self.assertRaises(PrivateStoreError):PrivateStore(path)
 def test_repr_private(self):self.assertNotIn(str(self.path),repr(self.store))

if __name__=='__main__':unittest.main()
