"""The pseudopotentials of Quantum ESPRESSO: the library SSSP downloaded once into the folder of the program.

§1 PURPOSE
    pw.x needs a pseudopotential file per element and the cutoffs of the plane waves that suit it. SSSP (Standard Solid
    State Pseudopotentials; Prandini, Marrazzo, Castelli, Mounet, Marzari, npj Comput. Mater. 4, 72, 2018) chooses for
    each element the file and the cutoffs tested against all-electron equations of state; «efficiency» — the cheaper set
    for everyday work. It is on the Materials Cloud Archive (record rcyfm-68h65, DOI 10.24435/materialscloud:f3-ym,
    CC BY 4.0 for the record; each file keeps the licence of its own library — LICENSE.txt of the record, kept next to
    the files). The program does not carry the files: they are downloaded on the computer of the user when asked
    («Установить программы» → Quantum ESPRESSO).
§2 ALGORITHM
    download(root): the JSON of the cutoffs and the archive of the files (urllib; without root certificates — the system
    curl, as install_tools), each checked by the MD5 the record publishes; the archive unpacked flat (names without
    folders, nothing outside the folder), the licence fetched too (no checksum published — a failure only noted).
    table(root): {element: (file, ecutwfc, ecutrho)} of the JSON (keys «filename», «cutoff_wfc», «cutoff_rho», Ry).
§4 SPECIFICATION
    LIBRARY (version, functional, protocol, URLs, MD5, sizes); PBESOL — SSSP 1.3.0 PBEsol efficiency of the
    same record; LDA — pslibrary files fetched by the element from the site of Quantum ESPRESSO (for_elements(library,
    elements) names them; choose(names, element, tag) -> file | None; cutoffs(text of the header) -> (wfc, rho) | None;
    download_elements); LIBRARIES {'PBE', 'PBEsol', 'LDA'}, main --library PBEsol; folder(root, library=None) -> Path; installed(root)
    -> bool; download(root, fetch=None, library=None) -> Path; table(root, library=None) -> dict; main(argv) (python -m
    modules.sextant.qe_pseudo --root DIR).
§6 NOTES
    The MD5 and the sizes are those of the record as of 2026-11-11 (its export JSON, read twice); a new version of the
    library is a new LIBRARY here.
§7 TESTS
    tests/sextant/test_qe_inputs.py (a fake archive and JSON through fetch).
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

RECORD = 'https://archive.materialscloud.org/api/records/rcyfm-68h65/files/{}/content'
LIBRARY = {
    'name': 'SSSP_1.3.0_PBE_efficiency',
    'functional': 'PBE',
    'json': ('SSSP_1.3.0_PBE_efficiency.json', '3153c4b20fc90a44fba0236627525644', 22376),
    'archive': ('SSSP_1.3.0_PBE_efficiency.tar.gz', 'a58f1b3373f330179fd0832c48bb9a52', 59513522),
    'license': 'LICENSE.txt',
}
# the same record, the library for PBEsol (MD5 and sizes of its file list, read 2026-11-15)
PBESOL = {
    'name': 'SSSP_1.3.0_PBEsol_efficiency',
    'functional': 'PBEsol',
    'json': ('SSSP_1.3.0_PBEsol_efficiency.json', '84fbbbd8f67b551abaec2f8a9df86801', 22459),
    'archive': ('SSSP_1.3.0_PBEsol_efficiency.tar.gz', 'b6cad0d97c86d3b43ae416d6e5d8b771', 60464715),
    'license': 'LICENSE.txt',
}
# LDA (Perdew — Zunger): SSSP has no such set. The files of pslibrary (A. Dal Corso, Comput. Mater. Sci. 95, 337,
# 2014; GPL) on the site of Quantum ESPRESSO, fetched for the elements of the crystal only: the page of an element
# lists its files, choose() takes one of them, the cutoffs are those its header suggests.
LDA = {
    'name': 'pslibrary_LDA',
    'functional': 'LDA',
    'kind': 'pslibrary',
    'tag': 'pz',
    'page': 'https://pseudopotentials.quantum-espresso.org/legacy_tables/ps-library/{}',
    'files': 'https://pseudopotentials.quantum-espresso.org/upf_files/{}',
}
LIBRARIES = {'PBE': LIBRARY, 'PBEsol': PBESOL, 'LDA': LDA}


def for_elements(library, elements):
    """The library with the elements a calculation needs (a library fetched by the element — LDA); others as they are."""
    if library.get('kind') != 'pslibrary':
        return library
    return {**library, 'elements': tuple(dict.fromkeys(elements))}


def choose(names, element, tag='pz'):
    """The file of an element among the names of its page: the functional tag («Si.pz-…»; not the relativistic
    «rel-pz»), ultrasoft (rrkjus) before PAW (kjpaw), the newest version of pslibrary, the fewest semicore states
    (the shortest name); None when there is none."""
    import re

    found = []
    for name in names:
        base = name.rsplit('/', 1)[-1]
        match = re.fullmatch(rf'{re.escape(element)}\.{re.escape(tag)}-(?:([a-z]+)-)?(rrkjus|kjpaw)_psl\.([\d.]+)\.UPF', base)
        if match:
            version = tuple(int(n) for n in match.group(3).split('.'))
            found.append((match.group(2) != 'rrkjus', tuple(-n for n in version), len(match.group(1) or ''), base))
    return min(found)[3] if found else None


def cutoffs(text):
    """(ecutwfc, ecutrho) Ry of the header of a pslibrary file («Suggested minimum cutoff for wavefunctions: 44. Ry»),
    or None."""
    import re

    wfc = re.search(r'Suggested minimum cutoff for wavefunctions:\s*([\d.]+)', text)
    rho = re.search(r'Suggested minimum cutoff for charge density:\s*([\d.]+)', text)
    return (float(wfc.group(1)), float(rho.group(1))) if wfc and rho else None


def _by_element(root, library):
    """{element: (file, ecutwfc, ecutrho)} of the files of a pslibrary folder (one file per element: the one choose
    takes among those that are there)."""
    target = folder(root, library)
    names = [p.name for p in target.glob('*.UPF')] if target.is_dir() else []
    found = {}
    for element in {name.split('.')[0] for name in names}:
        name = choose(names, element, library['tag'])
        if name is None:
            continue
        with open(target / name, encoding='utf-8', errors='replace') as stream:
            cut = cutoffs(stream.read(20000))
        if cut is not None:
            found[element] = (name, *cut)
    return found


def folder(root, library=None):
    return Path(root) / '.tools' / 'qe' / 'pseudo' / (library or LIBRARY)['name']


def _fetch(url):
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=300) as response:
            return response.read()
    except urllib.error.URLError as exc:
        if 'CERTIFICATE_VERIFY_FAILED' not in str(exc):
            raise
        from modules.sextant.install_tools import curl

        return curl(url)


def table(root, library=None):
    library = library or LIBRARY
    if library.get('kind') == 'pslibrary':
        return _by_element(root, library)
    target = folder(root, library)
    data = json.loads((target / library['json'][0]).read_text(encoding='utf-8'))
    return {element: (entry['filename'], float(entry['cutoff_wfc']), float(entry['cutoff_rho']))
            for element, entry in data.items() if isinstance(entry, dict) and 'filename' in entry}


def installed(root, library=None):
    try:
        found = table(root, library)
    except (OSError, ValueError, KeyError):
        return False
    if (library or LIBRARY).get('kind') == 'pslibrary':  # the files of the elements asked for (for_elements)
        return all(element in found for element in library.get('elements', ())) and (
            bool(found) or bool(library.get('elements')))
    return bool(found) and all((folder(root, library) / name).is_file() for name, _, _ in found.values())


def _checked(data, name, md5, size):
    if len(data) != size or hashlib.md5(data).hexdigest() != md5:
        raise ValueError(f'{name}: the download differs from the file of the record (size {len(data)}, expected {size})')
    return data


def download_elements(root, library, fetch=None):
    """The files of the elements of a pslibrary library (for_elements) that are not there yet."""
    import re

    fetch = fetch or _fetch
    target = folder(root, library)
    target.mkdir(parents=True, exist_ok=True)
    have = _by_element(root, library)
    for element in library.get('elements', ()):
        if element in have:
            continue
        page = fetch(library['page'].format(element.lower())).decode('utf-8', 'replace')
        name = choose(re.findall(r'href="([^"]+\.UPF)"', page), element, library['tag'])
        if name is None:
            raise ValueError(f'pslibrary: no {library["functional"]} pseudopotential of {element} on the site of '
                             'Quantum ESPRESSO')
        print(f'[pseudo] {name}', flush=True)
        data = fetch(library['files'].format(name))
        if cutoffs(data[:20000].decode('utf-8', 'replace')) is None:
            raise ValueError(f'{name}: not a pslibrary file (no suggested cutoffs in its header)')
        (target / name).write_bytes(data)
    return target


def download(root, fetch=None, library=None):
    fetch = fetch or _fetch
    library = library or LIBRARY
    if library.get('kind') == 'pslibrary':
        return download_elements(root, library, fetch)
    target = folder(root, library)
    target.mkdir(parents=True, exist_ok=True)
    name, md5, size = library['json']
    print(f'[pseudo] {name}', flush=True)
    text = _checked(fetch(RECORD.format(name)), name, md5, size)
    name, md5, size = library['archive']
    print(f'[pseudo] {name} ({size // 1_000_000} MB)', flush=True)
    archive = _checked(fetch(RECORD.format(name)), name, md5, size)
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
        for member in tar.getmembers():
            base = Path(member.name).name
            if not member.isfile() or not base or base.startswith('.'):
                continue
            stream = tar.extractfile(member)
            if stream is not None:
                (target / base).write_bytes(stream.read())
    (target / library['json'][0]).write_bytes(text)
    try:
        (target / library['license']).write_bytes(fetch(RECORD.format(library['license'])))
    except (OSError, ValueError) as exc:
        print(f'[pseudo] the licence file was not fetched: {exc}', flush=True)
    found = table(root, library)
    missing = [file for file, _, _ in found.values() if not (target / file).is_file()]
    if missing:
        raise ValueError('the archive lacks ' + ', '.join(missing[:5]))
    print(f'[pseudo] {len(found)} elements in {target}', flush=True)
    return target


def main(argv=None):
    from modules.sextant.install_tools import default_root

    parser = argparse.ArgumentParser(description='Download the SSSP pseudopotentials into .tools/qe/pseudo')
    parser.add_argument('--root', default=str(default_root()))
    parser.add_argument('--library', default='PBE', choices=sorted(LIBRARIES))
    args = parser.parse_args(argv)
    try:
        download(args.root, library=LIBRARIES[args.library])
    except (OSError, ValueError) as exc:
        print(f'[pseudo] ERROR: {exc}', flush=True)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
