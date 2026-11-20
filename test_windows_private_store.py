"""Windows protected store logic tests (any OS, fake backend, no skips).

These cover logic only. They do NOT show real DPAPI behaviour. Real DPAPI is
exercised by test_windows_native_store.py on native Windows.
"""
import os, tempfile, unittest, hashlib
from pathlib import Path
from windows_private_store import WindowsPrivateStore, WindowsPrivateStoreError as Err, DpapiBackend, MAX_BYTES

class FakeBackend:
    """Reversible stand-in, bound to the entropy. Not encryption."""
    def protect(self, data, entropy):
        return hashlib.sha256(entropy).digest() + data[::-1]
    def unprotect(self, blob, entropy):
        if blob[:32] != hashlib.sha256(entropy).digest():
            raise ValueError
        return blob[32:][::-1]

class Logic(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.path = Path(self.tmp.name) / 'priv'
    def tearDown(self): self.tmp.cleanup()
    def open(self):
        return WindowsPrivateStore(str(self.path), _backend=FakeBackend(), _platform='nt') if os.name != 'nt' else WindowsPrivateStore(str(self.path), _backend=FakeBackend())
    def test_refuses_non_windows_platform(self):
        with self.assertRaises(Err): WindowsPrivateStore(str(self.path), _backend=FakeBackend(), _platform='posix')
    def test_name_allowlist_and_bounds(self):
        s = self.new()
        for bad in ['../x.pem', 'A.pem', 'a.txt', 'a/b.json', '', 'a.pem\x00']:
            with self.assertRaises(Err): s.write(bad, b'x')
        with self.assertRaises(Err): s.write('a.pem', b'')
        with self.assertRaises(Err): s.write('a.pem', b'x' * (MAX_BYTES + 1))
        with self.assertRaises(Err): s.write('a.pem', 'str')
    def new(self):
        # Bypasses the constructor (drive-letter path rules) so logic runs on POSIX CI.
        s = object.__new__(WindowsPrivateStore)
        self.path.mkdir(exist_ok=True)
        s._root = self.path; s._chain = [self.path.parent, self.path]; s._backend = FakeBackend()
        return s
    def test_roundtrip_replace_no_temps_and_no_plaintext(self):
        s = self.new()
        s.write('session.json', b'synthetic-one'); self.assertEqual(s.read('session.json'), b'synthetic-one')
        s.write('session.json', b'two'); self.assertEqual(s.read('session.json'), b'two')
        self.assertEqual([p.name for p in self.path.iterdir()], ['session.json'])
        self.assertNotIn(b'two', (self.path / 'session.json').read_bytes())
    def test_blob_bound_to_name(self):
        s = self.new(); s.write('a.json', b'synthetic')
        (self.path / 'b.json').write_bytes((self.path / 'a.json').read_bytes())
        with self.assertRaises(Err): s.read('b.json')
    def test_corrupt_missing_empty_rejected(self):
        s = self.new()
        for n in ['a.json']:
            with self.assertRaises(Err): s.read(n)
        (self.path / 'a.json').write_bytes(b'')
        with self.assertRaises(Err): s.read('a.json')
        (self.path / 'a.json').write_bytes(b'garbage')
        with self.assertRaises(Err): s.read('a.json')
    def test_hardlink_rejected(self):
        s = self.new(); s.write('a.json', b'x'); os.link(self.path / 'a.json', self.path.parent / 'alias')
        with self.assertRaises(Err): s.read('a.json')
        with self.assertRaises(Err): s.write('a.json', b'y')
    def test_closed_store_rejected(self):
        s = self.new(); s.close()
        with self.assertRaises(Err): s.read('a.json')
        with self.assertRaises(Err): s.write('a.json', b'x')
    def test_failed_backend_leaves_no_temp(self):
        s = self.new()
        class Bad(FakeBackend):
            def protect(self, d, e): raise OSError
        s._backend = Bad()
        with self.assertRaises(Err): s.write('a.json', b'x')
        self.assertEqual(list(self.path.iterdir()), [])
    def test_repr_has_no_path(self):
        self.assertNotIn(str(self.path), repr(self.new()))

if os.name != 'nt':
    # Defined only off Windows, so a Windows run has no skips.
    class PosixOnly(Logic):
        def test_backend_refuses_off_windows(self):
            with self.assertRaises(Err): DpapiBackend()
        def test_posix_style_path_rejected_as_windows_path(self):
            with self.assertRaises(Err): self.open()
        def test_ancestor_replaced_by_symlink_after_construction_rejected(self):
            s = self.new(); s.write('a.json', b'x')
            moved = self.path.parent / 'moved'; os.rename(self.path.parent / 'priv', moved)
            os.symlink(moved, self.path.parent / 'priv')
            with self.assertRaises(Err): s.read('a.json')
            with self.assertRaises(Err): s.write('a.json', b'y')
        def test_symlink_file_rejected(self):
            s = self.new(); t = self.path.parent / 'target'; t.write_bytes(b'x'); os.symlink(t, self.path / 'a.json')
            with self.assertRaises(Err): s.read('a.json')
            with self.assertRaises(Err): s.write('a.json', b'y')
            self.assertEqual(t.read_bytes(), b'x')

if __name__ == '__main__': unittest.main()
