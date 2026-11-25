"""The settings of Azimuth (named Azimuth): one place that opens them.

§1 PURPOSE
    Every window reads and writes its preferences through open_settings(): the native store of the system
    (the registry on Windows, a plist on macOS) — or, when AZIMUTH_SETTINGS_FILE names a file, that INI file.
    The tests set it (tests/conftest.py), so a test run never reads or changes the settings of the user (a value
    saved by the user would change the input file a test expects; the registry may be read-only).
§2 the native store is named after the program — organisation and application «Azimuth» (it was
    «QuAIL» / «QCC Studio» before). The first time the new store is opened and is still empty,
    every key of the old one is copied into it once (MIGRATED marks it); the old store is left as it was, so
    an older version of the program still finds its settings. Not during the tests (PYTEST_CURRENT_TEST).
§4 SPECIFICATION
    open_settings() -> QSettings; ENVIRONMENT = 'AZIMUTH_SETTINGS_FILE'; ORGANISATION, APPLICATION;
    OLD_ORGANISATION, OLD_APPLICATION; MIGRATED; migrate(new, old) -> number of keys copied.
§7 TESTS
    tests/core/test_installation.py::test_settings_follow_the_environment.
"""

import os

ORGANISATION, APPLICATION = 'Azimuth', 'Azimuth'
OLD_ORGANISATION, OLD_APPLICATION = 'QuAIL', 'QCC Studio'  # the former names, copied once
MIGRATED = 'settings_copied_from_qcc_studio'
ENVIRONMENT = 'AZIMUTH_SETTINGS_FILE'
_checked = False


def migrate(new, old):
    """Copy every key of old into new when new has none yet (and mark it); returns the number of keys copied."""
    if new.contains(MIGRATED) or new.allKeys():
        return 0
    keys = old.allKeys()
    for key in keys:
        new.setValue(key, old.value(key))
    new.setValue(MIGRATED, True)
    new.sync()
    return len(keys)


def open_settings():
    global _checked
    from PySide6.QtCore import QSettings

    path = os.environ.get(ENVIRONMENT, '').strip()
    if path:
        return QSettings(path, QSettings.Format.IniFormat)
    store = QSettings(ORGANISATION, APPLICATION)
    if not _checked and not os.environ.get('PYTEST_CURRENT_TEST'):
        _checked = True
        try:
            migrate(store, QSettings(OLD_ORGANISATION, OLD_APPLICATION))
        except Exception:  # noqa: BLE001 — the settings of the old name are a convenience, never a reason to fail
            pass
    return store
