"""The tests never touch the real Keychain (2026-11-25): the fixture of conftest puts a dict in its place."""
from modules.sextant import keychain


def test_the_tests_use_a_dict_in_place_of_the_keychain(monkeypatch):
    called = []
    monkeypatch.setattr(keychain, '_find', lambda *args: called.append(args))
    assert keychain.STORE == {} and keychain.SESSION == {}
    assert keychain.get('Azimuth: user@server.example:22', 'user') is None
    keychain.put('Azimuth: user@server.example:22', 'user', 'pw')
    keychain.SESSION.clear()
    assert keychain.get('Azimuth: user@server.example:22', 'user') == 'pw'
    assert keychain.delete('Azimuth: user@server.example:22', 'user') and keychain.STORE == {}
    assert called == []


class _FakeAdvapi:
    """advapi32 of Windows in Python: the calls of keychain.py with the same ctypes structures."""
    windows = True

    def __init__(self):
        self.creds = {}

    def CredWriteW(self, pointer, flags):  # noqa: N802 — the name of the API
        cred = pointer._obj
        import ctypes
        self.creds[cred.TargetName] = (cred.UserName, ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize))
        return 1

    def CredReadW(self, target, kind, flags, out):  # noqa: N802
        import ctypes
        if kind != 1 or target not in self.creds:
            return 0
        user, blob = self.creds[target]
        self.buffer = (ctypes.c_ubyte * max(1, len(blob))).from_buffer_copy(blob or b'\0')
        self.cred = keychain._CREDENTIAL(Type=1, TargetName=target, UserName=user, CredentialBlobSize=len(blob),
                                         CredentialBlob=ctypes.cast(self.buffer, ctypes.POINTER(ctypes.c_ubyte)))
        out._obj.contents = self.cred
        return 1

    def CredFree(self, pointer):  # noqa: N802
        self.freed = True

    def CredDeleteW(self, target, kind, flags):  # noqa: N802
        return 1 if self.creds.pop(target, None) else 0


def test_on_windows_the_password_goes_to_the_credential_manager(monkeypatch):
    # the owner, 2026-11-25: with the box ticked a saved profile keeps its password on Windows too
    fake = _FakeAdvapi()
    monkeypatch.setattr(keychain, 'STORE', None)
    monkeypatch.setattr(keychain, '_lib', lambda: fake)
    service = 'Azimuth: user@server.example:22'
    assert keychain.available() and keychain.get(service, 'user') is None
    assert keychain.put(service, 'user', 'пароль-Ω')
    assert fake.creds[service] == ('user', 'пароль-Ω'.encode('utf-16-le'))  # UTF-16, as Windows keeps it
    keychain.SESSION.clear()
    assert keychain.get(service, 'user') == 'пароль-Ω' and fake.freed
    assert keychain.put(service, 'user', '', remember=True) and fake.creds[service] == ('user', b'')
    assert keychain.delete(service, 'user') and service not in fake.creds
    assert not keychain.delete(service, 'user')
    assert keychain.put(service, 'user', 'x', remember=False) and service not in fake.creds  # the session only
