"""Native Windows DPAPI tests with synthetic bytes. Run on Windows only.

On other systems this module defines no tests, so a run reports zero skips.
Run on Windows: python -m unittest -v test_windows_native_store
"""
import os, tempfile, unittest
from pathlib import Path
from windows_private_store import WindowsPrivateStore, WindowsPrivateStoreError as Err

if os.name == 'nt':
  class RealDpapi(unittest.TestCase):
      def setUp(self):
          self.tmp = tempfile.TemporaryDirectory(); self.path = Path(self.tmp.name) / 'priv'
      def tearDown(self): self.tmp.cleanup()
      def test_roundtrip_blob_is_not_plaintext(self):
          with WindowsPrivateStore(str(self.path)) as s:
              data = b'synthetic-not-a-secret-0123456789'
              s.write('session.json', data)
              self.assertEqual(s.read('session.json'), data)
              self.assertNotIn(data, (self.path / 'session.json').read_bytes())
              s.write('session.json', b'second'); self.assertEqual(s.read('session.json'), b'second')
      def test_blob_bound_to_name(self):
          with WindowsPrivateStore(str(self.path)) as s:
              s.write('a.json', b'synthetic')
              (self.path / 'b.json').write_bytes((self.path / 'a.json').read_bytes())
              with self.assertRaises(Err): s.read('b.json')
      def test_tamper_rejected(self):
          with WindowsPrivateStore(str(self.path)) as s:
              s.write('a.json', b'synthetic')
              raw = bytearray((self.path / 'a.json').read_bytes()); raw[-1] ^= 1
              (self.path / 'a.json').write_bytes(bytes(raw))
              with self.assertRaises(Err): s.read('a.json')
      def test_relative_unc_and_traversal_paths_rejected(self):
          for bad in ['relative', r'\\server\share\x', r'\\?\C:\x', str(self.path / '..' / 'x')]:
              with self.assertRaises(Err): WindowsPrivateStore(bad)
      def test_dot_components_in_raw_path_rejected(self):
          for bad in [str(Path(self.tmp.name)) + '\\.\\priv', str(Path(self.tmp.name)) + '\\priv\\.', str(Path(self.tmp.name)) + '\\\\priv']:
              with self.assertRaises(Err): WindowsPrivateStore(bad)
      def test_ancestor_swapped_to_junction_after_construction_rejected(self):
          import subprocess
          sub = Path(self.tmp.name) / 'anc'; sub.mkdir(); priv = sub / 'priv'
          with WindowsPrivateStore(str(priv)) as s:
              s.write('a.json', b'synthetic')
              moved = Path(self.tmp.name) / 'moved'; os.rename(sub, moved)
              subprocess.run(['cmd', '/c', 'mklink', '/J', str(sub), str(moved)], check=True, capture_output=True)
              with self.assertRaises(Err): s.read('a.json')
              with self.assertRaises(Err): s.write('a.json', b'y')
      def test_junction_rejected(self):
          import subprocess
          real = Path(self.tmp.name) / 'real'; real.mkdir(); link = Path(self.tmp.name) / 'link'
          subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(real)], check=True, capture_output=True)
          with self.assertRaises(Err): WindowsPrivateStore(str(link))
          with self.assertRaises(Err): WindowsPrivateStore(str(link / 'sub'))

if __name__ == '__main__': unittest.main()
