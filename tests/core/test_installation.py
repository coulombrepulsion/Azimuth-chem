"""Check diagnostic failures, including paths printable in legacy consoles."""

import importlib.util
from pathlib import Path
import shutil
import sys

import pytest

spec = importlib.util.spec_from_file_location('quail_verify', Path(__file__).parents[2] / 'verify_install.py')
verify = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = verify
spec.loader.exec_module(verify)


def test_diagnostic_failure_is_ascii(capsys):
    def fail():
        raise OSError('Неверный путь: молекула')

    assert verify.Check('Path', fail).run() is False
    output = capsys.readouterr().out
    assert output.isascii()
    assert '[FAIL]' in output


def test_asset_corruption_detected(tmp_path, monkeypatch):
    # SHA256 of empty input is an externally standardized, independently known value.
    (tmp_path / 'assets-manifest.json').write_text(
        '{"sample": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}'
    )
    (tmp_path / 'sample').write_bytes(b'')
    monkeypatch.setattr(verify, 'ROOT', tmp_path)
    assert verify.assets()[0]
    (tmp_path / 'sample').write_bytes(b'corrupt')
    assert not verify.assets()[0]


def test_missing_asset_fails(tmp_path, monkeypatch, capsys):
    (tmp_path / 'assets-manifest.json').write_text('{"missing": "unused"}')
    monkeypatch.setattr(verify, 'ROOT', tmp_path)
    assert not verify.Check('Assets', verify.assets).run()
    assert '[FAIL]' in capsys.readouterr().out


def test_missing_assets_are_named(tmp_path, monkeypatch):
    # the Windows run of 2026-10-29 — two pictures absent from the archive gave a bare FileNotFoundError
    (tmp_path / 'assets-manifest.json').write_text('{"a/one.webp": "x", "b/two.webp": "y"}', encoding='utf-8')
    monkeypatch.setattr(verify, 'ROOT', tmp_path)
    ok, message = verify.assets()
    assert not ok and '2 missing: a/one.webp, b/two.webp' in message and 'unpack the whole archive' in message


def test_manifest_names_only_files_of_the_repository():
    # the manifest listed two pictures that were never committed — the archive of GitHub failed verify_install
    import json
    import shutil
    import subprocess

    import pytest

    root = Path(__file__).parents[2]
    if shutil.which('git') is None or not (root / '.git').exists():
        pytest.skip('not a git checkout')
    done = subprocess.run(['git', 'ls-files'], cwd=root, capture_output=True, text=True, encoding='utf-8')
    if done.returncode != 0:
        pytest.skip('git ls-files failed')
    tracked = set(done.stdout.split('\n'))
    # the committed manifest (what GitHub gives) — the working copy may list pictures not committed yet
    head = subprocess.run(['git', 'show', 'HEAD:assets-manifest.json'], cwd=root, capture_output=True)
    if head.returncode != 0:
        pytest.skip('no committed manifest')
    manifest = json.loads(head.stdout.decode('utf-8'))
    assert sorted(set(manifest) - tracked) == []


def test_settings_follow_the_environment(tmp_path, monkeypatch):
    # AZIMUTH_SETTINGS_FILE — an INI file instead of the registry or the plist of the user (the tests use it)
    import pytest

    pytest.importorskip('PySide6')
    from azimuth import settings

    path = tmp_path / 'my.ini'
    monkeypatch.setenv(settings.ENVIRONMENT, str(path))
    s = settings.open_settings()
    s.setValue('theme', 'dark')
    s.sync()
    assert path.is_file() and 'theme=dark' in path.read_text(encoding='utf-8')
    monkeypatch.delenv(settings.ENVIRONMENT)
    native = settings.open_settings()
    assert native.organizationName() == 'Azimuth' and native.applicationName() == 'Azimuth'


def test_settings_of_the_old_name_are_copied_once(tmp_path):
    # the store «QuAIL / QCC Studio» is copied into «Azimuth / Azimuth» once, when the new one is empty
    import pytest

    pytest.importorskip('PySide6')
    from PySide6.QtCore import QSettings
    from azimuth import settings

    old = QSettings(str(tmp_path / 'old.ini'), QSettings.Format.IniFormat)
    old.setValue('theme', 'dark')
    old.setValue('servers/serv3', 'user@serv3')
    new = QSettings(str(tmp_path / 'new.ini'), QSettings.Format.IniFormat)
    assert settings.migrate(new, old) == 2
    assert new.value('theme') == 'dark' and new.value('servers/serv3') == 'user@serv3' and new.contains(settings.MIGRATED)
    old.setValue('theme', 'light')
    new.setValue('theme', 'dark')
    assert settings.migrate(new, old) == 0 and new.value('theme') == 'dark'  # once only; the new store wins
    assert old.value('theme') == 'light'  # the old store is left as it was


def test_windows_scripts_parse():
    """Setup.ps1 (it installs Python itself now) is read by the parser of PowerShell without errors; the
    scripts stay ASCII (Windows PowerShell 5 reads a file without BOM in the code page of the system)."""
    import shutil
    import subprocess

    import pytest

    root = Path(__file__).parents[2]
    for name in ('setup.ps1', 'windows_first_run.bat', 'Launch-Windows.bat'):
        assert (root / name).read_bytes().isascii(), name
    shell = shutil.which('powershell') or shutil.which('pwsh')
    if not shell:
        pytest.skip('no PowerShell')
    command = ("$e = $null; [System.Management.Automation.Language.Parser]::ParseFile("
               f"'{root / 'setup.ps1'}', [ref]$null, [ref]$e) | Out-Null; $e | ForEach-Object {{ $_.ToString() }}")
    found = subprocess.run([shell, '-NoProfile', '-Command', command], capture_output=True, text=True, timeout=120)
    assert found.returncode == 0 and not found.stdout.strip(), found.stdout + found.stderr


def test_manifest_matches_the_committed_files():
    """Every hash of the committed manifest is the hash of the committed file (what the archive gives). A
    student's report: the stale hashes of azimuth/locale/en.json and zh.json stopped every clean installation at 6/6
    (for the third time). The blobs of HEAD, not the working copy: git on Windows may change the line ends of it."""
    import hashlib
    import json
    import shutil
    import subprocess

    import pytest

    root = Path(__file__).parents[2]
    if shutil.which('git') is None or not (root / '.git').exists():
        pytest.skip('not a git checkout')
    head = subprocess.run(['git', 'show', 'HEAD:assets-manifest.json'], cwd=root, capture_output=True)
    if head.returncode != 0:
        pytest.skip('no committed manifest')
    manifest = json.loads(head.stdout.decode('utf-8'))
    names = list(manifest)
    batch = subprocess.run(['git', 'cat-file', '--batch'], cwd=root, capture_output=True,
                           input=''.join(f'HEAD:{n}\n' for n in names).encode('utf-8'))
    assert batch.returncode == 0
    data, at, wrong = batch.stdout, 0, []
    for name in names:
        end = data.index(b'\n', at)
        header = data[at:end].split()
        at = end + 1
        if header[-1] == b'missing':
            wrong.append(f'{name}: not committed')
            continue
        size = int(header[2])
        if hashlib.sha256(data[at:at + size]).hexdigest() != manifest[name]:
            wrong.append(name)
        at += size + 1
    assert wrong == [], 'update assets-manifest.json: ' + ', '.join(wrong[:10])


def test_the_linux_lock_pins_the_versions_of_the_other_platforms():
    """Linux x86_64 — the same versions as macOS and Windows, a sha256 of a wheel of PyPI for each (CPython
    3.13, manylinux; PySide6 6.12 asks glibc 2.34); setup.sh chooses it on Linux-x86_64, verify_install.py on Linux."""
    import re

    root = Path(__file__).parents[2]

    def pins(name):
        found = {}
        for line in (root / name).read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.startswith('#'):
                spec, *hashes = line.split()
                assert hashes and all(re.fullmatch(r'--hash=sha256:[0-9a-f]{64}', h) for h in hashes), line
                found[spec.split('==')[0].lower().replace('_', '-')] = spec.split('==')[1]
        return found

    linux = pins('requirements-lock-linux-x86_64.txt')
    assert linux == pins('requirements-lock-macos-arm64.txt') == pins('requirements-lock-win-amd64.txt')
    assert 'Linux-x86_64) lock=requirements-lock-linux-x86_64.txt' in (root / 'setup.sh').read_text(encoding='utf-8')
    assert "'requirements-lock-linux-x86_64.txt' if sys.platform.startswith('linux')" in (root / 'verify_install.py').read_text(encoding='utf-8')


def test_the_linux_launcher_adds_the_program_to_the_menu(tmp_path):
    """Launch-Linux.sh — bash, UTF-8 (the names of the menu in Russian and Chinese), LF; --install-desktop writes
    azimuth.desktop (the GUI launcher of .venv of
    the program folder, the links azimuth:// of the site) and the icons into XDG_DATA_HOME; --remove-desktop takes them
    away. Run in a copy of the folder with a stand-in .venv/bin/python."""
    import os
    import shutil
    import subprocess

    import pytest

    root = Path(__file__).parents[2]
    script = root / 'Launch-Linux.sh'
    assert script.read_text(encoding='utf-8').startswith('#!/usr/bin/env bash\n') and b'\r' not in script.read_bytes()
    bash = shutil.which('bash')
    if not bash or os.name == 'nt':
        pytest.skip('no bash')
    assert subprocess.run([bash, '-n', str(script)], capture_output=True).returncode == 0
    folder = tmp_path / 'Azimuth folder'  # a space in the path
    (folder / '.venv' / 'bin').mkdir(parents=True)
    python = folder / '.venv' / 'bin' / 'python'
    python.write_text('#!/bin/sh\n', encoding='utf-8')
    python.chmod(0o755)
    shutil.copy2(script, folder / script.name)
    shutil.copytree(root / 'assets' / 'app-icon', folder / 'assets' / 'app-icon')
    data = tmp_path / 'data'
    env = dict(os.environ, XDG_DATA_HOME=str(data), PATH='/usr/bin:/bin')
    done = subprocess.run([bash, str(folder / script.name), '--install-desktop'], capture_output=True, text=True, env=env, timeout=60)
    assert done.returncode == 0, done.stdout + done.stderr
    entry = (data / 'applications' / 'azimuth.desktop').read_text(encoding='utf-8')
    assert f'Exec="{folder}/.venv/bin/python" -B "{folder}/gui_launcher.py" %u' in entry
    assert 'Name[ru]=Азимут' in entry and 'Icon=azimuth' in entry and 'MimeType=x-scheme-handler/azimuth;' in entry
    assert 'Terminal=false' in entry and entry.startswith('[Desktop Entry]\n')
    for size in (16, 32, 48, 128, 256, 512):
        assert (data / 'icons' / 'hicolor' / f'{size}x{size}' / 'apps' / 'azimuth.png').is_file()
    done = subprocess.run([bash, str(folder / script.name), '--remove-desktop'], capture_output=True, text=True, env=env, timeout=60)
    assert done.returncode == 0 and not (data / 'applications' / 'azimuth.desktop').exists()
    assert not (data / 'icons' / 'hicolor' / '48x48' / 'apps' / 'azimuth.png').exists()



@pytest.mark.skipif(shutil.which('zsh') is None, reason='the launcher of Azimuth.app is a zsh script (macOS)')
def test_the_mac_launcher_checks_the_environment_once(tmp_path):
    # the check of Azimuth.app (PySide6, VTK, numpy, Qt WebEngine imported) took 1.8 s of every start; it runs again
    # only when the packages changed or a start failed on an import (gui_launcher.forget_check)
    import os
    import subprocess
    import time

    root = Path(__file__).resolve().parents[2]
    # 0.222.1 rewrote the launcher without its execute bit and Finder no longer started the program
    assert os.access(root / 'Azimuth.app' / 'Contents' / 'MacOS' / 'Azimuth', os.X_OK)
    app = tmp_path / 'Azimuth.app' / 'Contents' / 'MacOS'
    app.mkdir(parents=True)
    shutil.copy(root / 'Azimuth.app' / 'Contents' / 'MacOS' / 'Azimuth', app / 'Azimuth')
    (app / 'Azimuth').chmod(0o755)
    log = tmp_path / 'calls.log'
    python = tmp_path / '.venv' / 'bin' / 'python'
    python.parent.mkdir(parents=True)
    python.write_text(f'#!/bin/sh\necho "$1" >> {log}\nexit 0\n')
    python.chmod(0o755)
    packages = tmp_path / '.venv' / 'lib' / 'python3.13' / 'site-packages'
    packages.mkdir(parents=True)
    old = time.time() - 100
    os.utime(packages, (old, old))
    run = lambda: subprocess.run([str(app / 'Azimuth')], capture_output=True, timeout=30)  # noqa: E731
    run()
    assert log.read_text().split() == ['-c', '-B'] and (tmp_path / '.venv' / '.azimuth-checked').is_file()
    run()
    assert log.read_text().split() == ['-c', '-B', '-B']  # checked once: no import check
    os.utime(packages, (time.time() + 5, time.time() + 5))  # a package installed
    run()
    assert log.read_text().split() == ['-c', '-B', '-B', '-c', '-B']
    import gui_launcher

    stamp = tmp_path / '.venv' / '.azimuth-checked'
    assert gui_launcher.CHECK_STAMP == '.venv/.azimuth-checked' and stamp.is_file()


def test_the_launcher_checks_what_the_installation_verifies():
    """Launch-Windows.bat runs setup.ps1 again when its import check fails: it imported QtWebEngineWidgets, which the
    program no longer uses and verify_install does not check — on a Windows with a sound installation every start
    installed again (Windows check 2026-11-24). Its modules are those of verify_install.dependencies."""
    import re

    root = Path(__file__).parents[2]
    bat = (root / 'Launch-Windows.bat').read_text(encoding='ascii')
    line = next(l for l in bat.splitlines() if 'python.exe" -c' in l)
    imported = set(re.findall(r'import ([\w.]+(?:, [\w.]+)*)', line.split('-c', 1)[1].split('"')[1]))
    names = {n.strip() for group in imported for n in group.split(',')}
    assert 'PySide6.QtWebEngineWidgets' not in line and 'launch-check.txt' in line
    source = (root / 'verify_install.py').read_text(encoding='utf-8')
    for name in names - {'QtWidgets'}:
        assert f"'{name}'" in source, name


def test_setup_tries_the_official_index_when_the_mirror_fails():
    """pip of a computer set to a mirror (pip.ini) that timed out stopped the installation at 4/6 (Windows check
    2026-11-24): the installation is tried again with https://pypi.org/simple."""
    text = (Path(__file__).parents[2] / 'setup.ps1').read_text(encoding='ascii')
    assert '"--index-url", "https://pypi.org/simple"' in text
    assert 'Pip-Install @("--require-hashes", "-r", $lock)' in text
    assert 'Run-Python @("-m", "pip", "install", "--require-hashes"' not in text
