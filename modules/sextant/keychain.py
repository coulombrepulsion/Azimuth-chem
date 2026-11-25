"""Sextant: the password of a server in the Keychain of macOS or the Credential Manager of Windows.

HEADER
    The password of the server is never written into the settings or a profile file. It is kept for the session in
    memory, and — when the user ticks «Запомнить в Связке ключей» — in the login Keychain of macOS, where macOS
    protects it (the system may ask for permission the first time); on Windows — when the user ticks «Запомнить в
    Windows» — in the Credential Manager, which encrypts it with the key of the user's Windows account (DPAPI; the
    owner, 2026-11-25: «когда сохраняешь профиль сервера — должен же сохраняться пароль, если поставить галочку?»).
    On other systems only the memory of the session.
    Wilkinson convention, sections 1-8.

§2 ALGORITHM The Security framework through ctypes: SecKeychainFindGenericPassword (then SecKeychainItemFreeContent),
    SecKeychainAddGenericPassword, SecKeychainItemModifyAttributesAndData for an item that exists,
    SecKeychainItemDelete. Windows: advapi32 through ctypes — CredReadW / CredWriteW / CredDeleteW, a generic
    credential (CRED_TYPE_GENERIC) with the service as its target name, the login as its user name, the password as
    UTF-16-LE bytes, kept for this user on this computer (CRED_PERSIST_LOCAL_MACHINE). Service «Azimuth:
    user@host:port», account — the login. No password ever goes on a command line.
§4 SPECIFICATION
    available() -> bool; get(service, account) -> str | None; put(service, account, password) -> bool;
    delete(service, account) -> bool; service_for(profile) -> str. SESSION: {service: password} of this run.
    STORE: None, or a dict {service: password} that stands for the Keychain (the tests set it for every test, so a run
    never reads or writes the real Keychain of the computer — 2026-11-25: a test window showed the saved password of a
    real server profile).
§8' ROBUSTNESS
    Any failure of the framework returns None / False — the password is then asked again, nothing breaks.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sys

SESSION = {}
STORE = None
_security = None


def _lib():
    """The library of the store of the system: Security.framework (macOS), advapi32 (Windows), else None."""
    global _security
    if _security is None:
        _security = False
        try:
            if sys.platform == 'darwin':
                _security = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/Security.framework/Security')
            elif sys.platform == 'win32':
                _security = _windows_lib()
        except (OSError, AttributeError):
            _security = False
    return _security or None


class _FILETIME(ctypes.Structure):
    _fields_ = [('low', ctypes.c_uint32), ('high', ctypes.c_uint32)]


class _CREDENTIAL(ctypes.Structure):
    _fields_ = [('Flags', ctypes.c_uint32), ('Type', ctypes.c_uint32), ('TargetName', ctypes.c_wchar_p),
                ('Comment', ctypes.c_wchar_p), ('LastWritten', _FILETIME), ('CredentialBlobSize', ctypes.c_uint32),
                ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)), ('Persist', ctypes.c_uint32),
                ('AttributeCount', ctypes.c_uint32), ('Attributes', ctypes.c_void_p),
                ('TargetAlias', ctypes.c_wchar_p), ('UserName', ctypes.c_wchar_p)]


_GENERIC = 1  # CRED_TYPE_GENERIC
_LOCAL_MACHINE = 2  # CRED_PERSIST_LOCAL_MACHINE: this user, this computer, after a restart too


def _windows_lib():
    lib = ctypes.WinDLL('advapi32', use_last_error=True)
    lib.CredReadW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                              ctypes.POINTER(ctypes.POINTER(_CREDENTIAL))]
    lib.CredReadW.restype = ctypes.c_int
    lib.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIAL), ctypes.c_uint32]
    lib.CredWriteW.restype = ctypes.c_int
    lib.CredDeleteW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
    lib.CredDeleteW.restype = ctypes.c_int
    lib.CredFree.argtypes = [ctypes.c_void_p]
    lib.CredFree.restype = None
    lib.windows = True
    return lib


def _windows(lib):
    return getattr(lib, 'windows', False) is True


def _win_get(lib, service):
    found = ctypes.POINTER(_CREDENTIAL)()
    if not lib.CredReadW(service, _GENERIC, 0, ctypes.byref(found)):
        return None
    try:
        cred = found.contents
        return ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize).decode('utf-16-le')
    finally:
        lib.CredFree(found)


def _win_put(lib, service, account, password):
    blob = password.encode('utf-16-le')
    buffer = (ctypes.c_ubyte * max(1, len(blob))).from_buffer_copy(blob or b'\0')
    cred = _CREDENTIAL(Type=_GENERIC, TargetName=service, CredentialBlobSize=len(blob),
                       CredentialBlob=ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)), Persist=_LOCAL_MACHINE,
                       UserName=account, Comment='Azimuth')
    return bool(lib.CredWriteW(ctypes.byref(cred), 0))


def available():
    return _lib() is not None


def service_for(profile):
    return f'Azimuth: {profile.address()}'


def _find(lib, service, account):
    s, a = service.encode('utf-8'), account.encode('utf-8')
    length = ctypes.c_uint32()
    data = ctypes.c_void_p()
    item = ctypes.c_void_p()
    status = lib.SecKeychainFindGenericPassword(None, len(s), s, len(a), a, ctypes.byref(length), ctypes.byref(data),
                                                ctypes.byref(item))
    return status, length, data, item


def get(service, account):
    if service in SESSION:
        return SESSION[service]
    if STORE is not None:
        return STORE.get(service)
    lib = _lib()
    if lib is None:
        return None
    try:
        if _windows(lib):
            value = _win_get(lib, service)
            if value is not None:
                SESSION[service] = value
            return value
        status, length, data, item = _find(lib, service, account)
        if status != 0:
            return None
        try:
            value = ctypes.string_at(data, length.value).decode('utf-8')
        finally:
            lib.SecKeychainItemFreeContent(None, data)
        SESSION[service] = value
        return value
    except Exception:  # noqa: BLE001 — the Keychain is a convenience, never an error of the program
        return None


def put(service, account, password, remember=True):
    SESSION[service] = password
    if not remember:
        return True
    if STORE is not None:
        STORE[service] = password
        return available()
    lib = _lib()
    if lib is None:
        return False
    try:
        if _windows(lib):
            return _win_put(lib, service, account, password)
        p = password.encode('utf-8')
        status, length, data, item = _find(lib, service, account)
        if status == 0:
            lib.SecKeychainItemFreeContent(None, data)
            return lib.SecKeychainItemModifyAttributesAndData(item, None, len(p), p) == 0
        s, a = service.encode('utf-8'), account.encode('utf-8')
        return lib.SecKeychainAddGenericPassword(None, len(s), s, len(a), a, len(p), p, None) == 0
    except Exception:  # noqa: BLE001
        return False


def delete(service, account):
    SESSION.pop(service, None)
    if STORE is not None:
        return STORE.pop(service, None) is not None
    lib = _lib()
    if lib is None:
        return False
    try:
        if _windows(lib):
            return bool(lib.CredDeleteW(service, _GENERIC, 0))
        status, length, data, item = _find(lib, service, account)
        if status != 0:
            return False
        lib.SecKeychainItemFreeContent(None, data)
        return lib.SecKeychainItemDelete(item) == 0
    except Exception:  # noqa: BLE001
        return False
