"""Links azimuth://: a page of the site asks the installed program to open a molecule in Compass.

§1 PURPOSE
    «Открыть в Компасе» of an Atlas topic worked only inside the program (a console message read by
    modules/atlas/browser.py). The Atlas now also lives on the site, in a plain browser: its button opens the address
    azimuth://compass/water, the system gives it to the program, the program shows the molecule.
§2 RULES
    1. The only address understood: azimuth://compass/<key> (the scheme and «compass» without regard to case, one
       optional «/» at the end); <key> is one of MOLECULES — lower-case Latin letters and digits, 1…40 characters.
       No query, no fragment, no user or port, nothing after the key.
    2. A link comes from the web and is not trusted: it names a molecule of the program's own library and nothing
       else — no file, no path, no geometry, no command. Whatever does not fit §2.1 is refused (parse → None) and
       nothing is done; the caller writes it to the log.
    3. MOLECULES = {key: the name of the molecule in the library of Compass} — the table of «Открыть в Компасе»
       (it was modules/atlas/browser.ATLAS_MOLECULES; the keys are those of <meta name="qc-molecules"> of the pages).
    4. Windows: the system starts the program with the address as an argument, the command of the scheme is kept in
       the registry of the user (HKEY_CURRENT_USER\\Software\\Classes\\azimuth, no administrator rights):
       command_line(executable, script) — «"<executable>" "%1"» for the built program, «"<pythonw>" -B
       "<gui_launcher.py>" "%1"» for the program run from its folder; register(command, registry) writes it when it
       is not there yet or differs (the installation started last answers the links) and says whether it wrote.
       macOS: the scheme is declared in Info.plist (CFBundleURLTypes), the address arrives as an event of the system.
       The system reads Info.plist when it first meets the application and not again: an Azimuth.app that lies in
       its folder and is updated in place (git) keeps the old description, and the address is answered by «no
       application knows how to open» (seen on 2026-11-11). register_bundle(bundle, marker, version, run) therefore
       asks the system to read the application again (lsregister -f <bundle>) once for every version and place of
       the program — the marker file keeps «version, tab, path» of the last time it did; True when it asked. No
       bundle or no lsregister — nothing is done.
    5. link_in(argv) — the first argument that begins with the scheme (any case), else None: the address as given,
       not yet checked.
§3 INTERFACE
    SCHEME = 'azimuth'; MOLECULES; Link(action, key, name); parse(text) -> Link | None; address(key) -> str
    (ValueError for a key not in MOLECULES); link_in(argv) -> str | None; command_line(executable, script=None) ->
    str; register(command, registry=None) -> bool (registry — an object with the functions of winreg; None — winreg
    itself, Windows only); register_bundle(bundle, marker, version, run=None, tool=LSREGISTER) -> bool (run — as
    subprocess.run; None — subprocess.run itself).
§4 TESTS
    tests/runtime/test_links.py — the addresses accepted and refused written out by hand, every key leads to a
    molecule the library has, the command lines against the rules of quoting of Windows, the registry as a
    dictionary of the test's own, the registration of the bundle with a run that only records its command.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SCHEME = 'azimuth'
MOLECULES = {
    'water': 'Вода · H₂O', 'ammonia': 'Аммиак · NH₃', 'methane': 'Метан · CH₄', 'co2': 'Диоксид углерода · CO₂',
    'bf3': 'Трифторид бора · BF₃', 'benzene': 'Бензол · C₆H₆', 'ethene': 'Этен (этилен) · C₂H₄',
    'hf': 'Фтороводород · HF', 'n2': 'Азот · N₂', 'butadiene': 'Бута-1,3-диен · C₄H₆', 'naphthalene': 'Нафталин · C₁₀H₈',
    'pyridine': 'Пиридин · C₅H₅N', 'pyrrole': 'Пиррол · C₄H₅N', 'furan': 'Фуран · C₄H₄O',
    'formaldehyde': 'Метаналь (формальдегид) · CH₂O', 'phenol': 'Фенол · C₆H₆O', 'so3': 'Триоксид серы · SO₃',
    'h2o2': 'Пероксид водорода · H₂O₂', 'ethane': 'Этан · C₂H₆', 'cyclohexane': 'Циклогексан · C₆H₁₂',
    'butane': 'Бутан · C₄H₁₀', 'acetic': 'Этановая (уксусная) кислота · C₂H₄O₂', 'methanol': 'Метанол · CH₄O',
    'acetone': 'Пропан-2-он (ацетон) · C₃H₆O', 'hcl': 'Хлороводород · HCl', 'ethanol': 'Этанол · C₂H₆O',
}
_ADDRESS = re.compile(r'azimuth://compass/([a-z0-9]{1,40})/?', re.ASCII)
_HEAD = re.compile(r'(azimuth://compass/)(.*)', re.ASCII | re.IGNORECASE | re.DOTALL)
REGISTRY_KEY = r'Software\Classes\azimuth'
LSREGISTER = ('/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/'
              'lsregister')


@dataclass(frozen=True)
class Link:
    action: str  # 'compass'
    key: str
    name: str  # the name in the library of Compass


def parse(text):
    """§2.1, §2.2: the link of an address, or None for anything else."""
    if not isinstance(text, str) or len(text) > 200:
        return None
    head = _HEAD.fullmatch(text.strip())
    if head is None:
        return None
    found = _ADDRESS.fullmatch(head.group(1).lower() + head.group(2))
    if found is None or found.group(1) not in MOLECULES:
        return None
    return Link('compass', found.group(1), MOLECULES[found.group(1)])


def address(key):
    if key not in MOLECULES:
        raise ValueError(f'No molecule {key!r} for a link.')
    return f'{SCHEME}://compass/{key}'


def link_in(argv):
    """§2.5."""
    for argument in argv:
        if isinstance(argument, str) and argument[:len(SCHEME) + 1].lower() == SCHEME + ':':
            return argument
    return None


def command_line(executable, script=None):
    """§2.4: the command of the scheme. A path with a quotation mark cannot be a path of Windows — refused."""
    parts = [str(executable)] + ([str(script)] if script is not None else [])
    for part in parts:
        if '"' in part or not part.strip():
            raise ValueError(f'Not a path for a command: {part!r}')
    if script is None:
        return f'"{parts[0]}" "%1"'
    return f'"{parts[0]}" -B "{parts[1]}" "%1"'


def register(command, registry=None):
    """§2.4: the scheme in the registry of the user; True when something was written."""
    if registry is None:
        import winreg as registry
    root = registry.HKEY_CURRENT_USER
    shell = REGISTRY_KEY + r'\shell\open\command'
    try:
        with registry.OpenKey(root, shell) as key:
            present = registry.QueryValueEx(key, '')[0]
        with registry.OpenKey(root, REGISTRY_KEY) as key:
            registry.QueryValueEx(key, 'URL Protocol')
    except OSError:
        present = None
    if present == command:
        return False
    with registry.CreateKey(root, REGISTRY_KEY) as key:
        registry.SetValueEx(key, '', 0, registry.REG_SZ, 'URL:Azimuth')
        registry.SetValueEx(key, 'URL Protocol', 0, registry.REG_SZ, '')
    with registry.CreateKey(root, shell) as key:
        registry.SetValueEx(key, '', 0, registry.REG_SZ, command)
    return True


def register_bundle(bundle, marker, version, run=None, tool=LSREGISTER):
    """§2.4, macOS: the system reads the application again, once for a version and a place; True when asked."""
    from pathlib import Path

    bundle, marker, tool = Path(bundle), Path(marker), Path(tool)
    if not (bundle / 'Contents' / 'Info.plist').is_file() or not tool.is_file():
        return False
    stamp = f'{version}\t{bundle}'
    try:
        if marker.read_text(encoding='utf-8') == stamp:
            return False
    except (OSError, UnicodeDecodeError):
        pass
    if run is None:
        import subprocess

        run = subprocess.run
    done = run([str(tool), '-f', str(bundle)], capture_output=True, timeout=30)
    if getattr(done, 'returncode', 1) != 0:
        return False  # not marked: asked again at the next start
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(stamp, encoding='utf-8')
    return True
