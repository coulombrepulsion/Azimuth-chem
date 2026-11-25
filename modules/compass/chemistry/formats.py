"""Molecule files of other programs: reading and writing for Compass.

Read: MDL molfile / SDF (V2000 and V3000; every record — read_sdf_records, each in its own tab),
       Tripos MOL2, PDB (ATOM/HETATM, CONECT; several MODEL frames → steps, pdb_trajectory), Gaussian input (.gjf/.com,
       Cartesian coordinates), Gaussian output (.log/.out:
       every printed orientation with its SCF energy → optimization steps), Molden (.molden:
       [Atoms], and [GEOMETRIES] with [GEOCONV] energies → steps), XYZ with several frames
       (ORCA _trj.xyz and similar → steps), SMILES (from_smiles: a 3D starting structure).
Write: molfile, SDF, MOL2, PDB (V3000 molfile for more than 999 atoms or bonds; SMILES —
       modules/compass/chemistry/pubchem.to_smiles, InChI — PubChem).
Bond orders: those of the file (aromatic → alternating single/double, the Kekulé form, so that the
structure stays drawable); files without bonds get them from distances, as XYZ.
"""

import re
from dataclasses import replace

from azimuth.core import SYMBOLS
from azimuth.core import read_xyz  # noqa: F401 — formats.read_xyz is named by the tests
from azimuth.i18n import tr
from modules.compass.chemistry.formats_common import _f, readable, _symbol, _molecule, kekule  # noqa: F401 — also named from here
from modules.compass.chemistry.formats_outputs import read_gaussian_input, read_orca_input, Trajectory, Step, read_gaussian_log, read_molden, read_xyz_frames, xyz_trajectory, xyz_frame_count  # noqa: F401 — also named from here
from modules.compass.chemistry.formats_smiles import from_smiles  # noqa: F401 — also named from here


def read_text(path):
    """The text of a structure file: UTF-8 (with or without BOM); a file saved by an older Windows program
    (cp1251) is read as such instead of failing."""
    from pathlib import Path

    data = Path(path).read_bytes()
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return data.decode('cp1251', errors='replace')


# -- MDL molfile / SDF -----------------------------------------------------------------------------
@readable('Молфайл')
def read_mol(text):
    lines = text.replace('\r\n', '\n').replace('\r', '\n').replace('\ufeff', '').split('\n')
    if len(lines) < 4:
        raise ValueError(tr('Молфайл: нет строки счётчиков.'))
    # the counts line is the fourth; when it is not (an empty line lost or added before the header), the line
    # with V2000/V3000 is taken and the header is the three lines above it
    at = 3
    if not re.search(r'V[23]000', lines[3]):
        at = next((k for k in range(min(len(lines), 12)) if re.search(r'V[23]000', lines[k])), 3)
    if at != 3:
        lines = [''] * max(0, 3 - at) + lines[max(0, at - 3):]
    title = lines[0].strip()
    counts = lines[3]
    if 'V3000' in counts:
        atoms, bonds, part = [], [], None
        for line in lines[4:]:
            body = line[7:].strip() if line.startswith('M  V30') else None
            if body is None:
                if line.startswith('M  END'):
                    break
                continue
            if body.startswith('BEGIN'):
                part = body.split()[1]
                continue
            if body.startswith('END'):
                part = None
                continue
            f = body.split()
            if part == 'ATOM':
                atoms.append((_symbol(f[1]), _f(f[2]), _f(f[3]), _f(f[4])))
            elif part == 'BOND':
                bonds.append((int(f[2]) - 1, int(f[3]) - 1, int(f[1])))
        return _molecule(title, atoms, bonds)
    try:
        n_atoms, n_bonds = int(counts[0:3]), int(counts[3:6])
    except ValueError:
        # some programs do not keep the columns («12 11 0 0 …», tabs) — then by whitespace
        fields = counts.split()
        try:
            n_atoms, n_bonds = int(fields[0]), int(fields[1])
        except (ValueError, IndexError):
            raise ValueError(tr('Молфайл: неверная строка счётчиков.')) from None
    if len(lines) < 4 + n_atoms + n_bonds:
        raise ValueError(tr('Молфайл: атомов или связей меньше, чем в строке счётчиков.'))
    atoms, bonds = [], []
    for line in lines[4 : 4 + n_atoms]:
        try:
            atoms.append(
                (_symbol(line[31:34].strip() or line.split()[3]), _f(line[0:10]), _f(line[10:20]), _f(line[20:30]))
            )
        except (ValueError, IndexError):
            f = line.split()  # not in the columns
            atoms.append((_symbol(f[3]), _f(f[0]), _f(f[1]), _f(f[2])))
    for line in lines[4 + n_atoms : 4 + n_atoms + n_bonds]:
        try:
            a, b, o = int(line[0:3]), int(line[3:6]), int(line[6:9])
        except ValueError:
            a, b, o = (int(x) for x in line.split()[:3])
        bonds.append((a - 1, b - 1, 1.5 if o == 4 else min(max(o, 1), 3)))
    return _molecule(title or tr('Молфайл'), atoms, bonds)


CHARGE_CODES = {1: 3, 2: 2, 3: 1, 4: 0, 5: -1, 6: -2, 7: -3}  # the «ccc» column of the V2000 atom block (4: a doublet)


def mol_charges(text):
    """The formal charges of the atoms of a molfile record ([int] per atom): «M CHG» lines (they supersede the
    charge column of the atom block, CTfile format), else the column «ccc» (characters 37–39); V3000 — «CHG=n» of the
    atom lines. Nitrate, chlorate, chloride of an SDF database came without them: the total charge was guessed from
    the bonds (Cl⁻ as a neutral doublet atom, NO₃⁻ as +1) and the skeleton got hydrogens on its O⁻."""
    lines = text.replace('\r\n', '\n').replace('\r', '\n').replace('\ufeff', '').split('\n')
    at = next((k for k in range(min(len(lines), 12)) if re.search(r'V[23]000', lines[k])), None)
    if at is None:
        return []
    if 'V3000' in lines[at]:
        charges, inside = [], False
        for line in lines[at + 1:]:
            body = line[7:].strip() if line.startswith('M  V30') else None
            if body is None:
                if line.startswith('M  END'):
                    break
                continue
            if body.startswith('BEGIN ATOM'):
                inside = True
            elif body.startswith('END ATOM'):
                break
            elif inside:
                found = re.search(r'\bCHG=(-?\d+)', body)
                charges.append(int(found.group(1)) if found else 0)
        return charges
    counts = lines[at]
    try:
        n_atoms, n_bonds = int(counts[0:3]), int(counts[3:6])
    except ValueError:
        try:
            n_atoms, n_bonds = (int(x) for x in counts.split()[:2])
        except ValueError:
            return []
    block = lines[at + 1: at + 1 + n_atoms]
    charges = []
    for line in block:
        try:
            charges.append(CHARGE_CODES.get(int(line[36:39]), 0))
        except ValueError:
            charges.append(0)
    listed = [line for line in lines[at + 1 + n_atoms + n_bonds:] if line.startswith('M  CHG')]
    if listed:
        charges = [0] * n_atoms
        for line in listed:
            fields = line.split()[3:]
            for k in range(0, len(fields) - 1, 2):
                try:
                    atom, value = int(fields[k]), int(fields[k + 1])
                except ValueError:
                    continue
                if 1 <= atom <= n_atoms:
                    charges[atom - 1] = value
    return charges


def sdf_charges(text):
    """Mol_charges of every record of an SDF, in the order of read_sdf_records."""
    records = re.split(r'^\$\$\$\$[^\n]*$', text.replace('\r\n', '\n').replace('\r', '\n'), flags=re.M)
    out = []
    for k, r in enumerate(records):
        if not r.strip():
            continue
        r = r[1:] if k and r.startswith('\n') else r
        out.append(mol_charges(r))
    return out


# the data items that name a record whose header line is empty (RDKit writes «> <Name>», PubChem
# PUBCHEM_IUPAC_NAME, ChEMBL chembl_id) — the first one found, in this order, case aside
NAME_ITEMS = ('name', 'title', 'compound', 'compound name', 'molecule name', 'common name', 'iupac name', 'iupac',
              'pubchem_iupac_name', 'pubchem_iupac_openeye_name', 'chembl_id', 'pubchem_compound_cid', 'id', 'cas')
_NO_NAME = ('', 'nan', 'none', 'null', 'n/a', 'na', '-', '?')


def sdf_items(record):
    """The data items of an SDF record after «M END»: «> <Name> (1)» and its value lines → {name: value}."""
    items, key, value = {}, None, []
    tail = re.split(r'^M  END[^\n]*$', record, maxsplit=1, flags=re.M)
    for line in (tail[1] if len(tail) > 1 else '').split('\n'):
        head = re.match(r'^>.*?<([^>]*)>', line)
        if head:
            if key is not None:
                items.setdefault(key, '\n'.join(value).strip())
            key, value = head.group(1).strip(), []
        elif key is not None:
            if line.strip():
                value.append(line.rstrip())
            else:  # an empty line ends the value
                items.setdefault(key, '\n'.join(value).strip())
                key, value = None, []
    if key is not None:
        items.setdefault(key, '\n'.join(value).strip())
    return items


def sdf_name(items):
    """The name of a record by its data items, '' when none («nan» of a table is none); underscores of a name
    without spaces («Nitrilotriacetic_acid_(NTA)») are the spaces."""
    lower = {k.lower(): v for k, v in items.items()}
    for key in NAME_ITEMS:
        value = (lower.get(key) or '').split('\n')[0].strip()
        if value.lower() not in _NO_NAME:
            return value.replace('_', ' ') if ' ' not in value else value
    return ''


def sdf_properties(text):
    """The data items of every record of an SDF file ({name: value}), in the order of read_sdf_records (empty
    records skipped) — logK, names, sources of a database go with each structure into a queue (BatchItem.props)."""
    records = re.split(r'^\$\$\$\$[^\n]*$', text.replace('\r\n', '\n').replace('\r', '\n'), flags=re.M)
    return [sdf_items(r) for r in records if r.strip()]


def read_sdf_records(text):
    """Every record of an SDF file (records end with «$$$$»; empty ones are skipped) → [Molecule]; a
    record with an empty header line is named by its data items (sdf_name), it was «Молфайл» for every one."""
    records = re.split(r'^\$\$\$\$[^\n]*$', text.replace('\r\n', '\n').replace('\r', '\n'), flags=re.M)
    # only the end of the «$$$$» line is cut — the first header line (the name) may be empty, and lstrip took
    # it too, so the counts line moved up (the PubChem, RDKit and Open Babel files without a name)
    found = []
    for k, r in enumerate(records):
        if not r.strip():
            continue
        r = r[1:] if k and r.startswith('\n') else r  # the end of the «$$$$» line (the first record has none)
        molecule = read_mol(r)
        if not r.split('\n')[0].strip():
            name = sdf_name(sdf_items(r))
            if name:
                molecule = replace(molecule, title=name)
        found.append(molecule)
    if not found:
        raise ValueError(tr('SDF: нет ни одной молекулы.'))
    return found


def write_mol(molecule, bonds):
    if len(molecule.atoms) > 999 or len(bonds) > 999:  # the V2000 counts have three digits
        return write_mol_v3000(molecule, bonds)
    head = f'{molecule.title[:80]}\n  Azimuth\n\n{len(molecule.atoms):3d}{len(bonds):3d}  0  0  0  0  0  0  0  0999 V2000\n'
    rows = ''.join(
        f'{a.x:10.4f}{a.y:10.4f}{a.z:10.4f} {a.symbol:<3} 0  0  0  0  0  0  0  0  0  0  0  0\n' for a in molecule.atoms
    )
    links = ''.join(f'{i + 1:3d}{j + 1:3d}{int(o):3d}  0\n' for i, j, o in bonds)
    return head + rows + links + 'M  END\n'


def write_mol_v3000(molecule, bonds):
    """The extended (V3000) molfile — no limit of 999 atoms."""
    lines = [molecule.title[:80], '  Azimuth', '', '  0  0  0     0  0            999 V3000', 'M  V30 BEGIN CTAB',
             f'M  V30 COUNTS {len(molecule.atoms)} {len(bonds)} 0 0 0', 'M  V30 BEGIN ATOM']
    lines += [f'M  V30 {k + 1} {a.symbol} {a.x:.4f} {a.y:.4f} {a.z:.4f} 0' for k, a in enumerate(molecule.atoms)]
    lines += ['M  V30 END ATOM', 'M  V30 BEGIN BOND']
    lines += [f'M  V30 {k + 1} {int(o)} {i + 1} {j + 1}' for k, (i, j, o) in enumerate(bonds)]
    lines += ['M  V30 END BOND', 'M  V30 END CTAB', 'M  END']
    return '\n'.join(lines) + '\n'


def write_sdf(molecule, bonds):
    return write_mol(molecule, bonds) + '$$$$\n'


# -- MOL2 ------------------------------------------------------------------------------------------
@readable('MOL2')
def read_mol2(text):
    # a file of several molecules — the first one (before, the sections of the last overwrote it)
    blocks = re.split(r'(?=@<TRIPOS>MOLECULE)', text, flags=re.I)
    text = next((b for b in blocks if re.search(r'@<TRIPOS>ATOM', b, re.I)), text)
    sections = re.split(r'@<TRIPOS>(\w+)', text)
    parts = {}
    for k in range(1, len(sections) - 1, 2):
        parts.setdefault(sections[k].upper(), sections[k + 1])
    if 'ATOM' not in parts:
        raise ValueError(tr('MOL2: нет раздела ATOM.'))
    title = (parts.get('MOLECULE', '').strip().splitlines() or [''])[0].strip()
    atoms, ids = [], {}
    for n, line in enumerate(parts['ATOM'].strip().splitlines(), start=1):
        f = line.split()
        if len(f) < 6:
            continue
        kind = f[5].split('.')[0]
        if kind.upper() == 'LP':  # a lone pair of a force field, not an atom
            continue
        try:
            symbol = 'X' if kind.capitalize() == 'Du' else _symbol(kind)
        except ValueError:
            symbol = _symbol(f[1])  # an atom type that is not an element — the atom name
        try:
            atoms.append((symbol, _f(f[2]), _f(f[3]), _f(f[4])))
        except ValueError as exc:
            raise ValueError(tr(f'MOL2, атом {n}: {exc}')) from None
        ids[f[0]] = len(atoms) - 1
    bonds = []
    for line in parts.get('BOND', '').strip().splitlines():
        f = line.split()
        if len(f) >= 4 and f[1] in ids and f[2] in ids and f[3].lower() != 'nc':  # nc: «not connected»
            o = {'1': 1, '2': 2, '3': 3, 'ar': 1.5, 'am': 1}.get(f[3].lower(), 1)
            bonds.append((ids[f[1]], ids[f[2]], o))
    return _molecule(title or 'MOL2', atoms, bonds if 'BOND' in parts else None)


def _cdxml_tree(text):
    import xml.etree.ElementTree as ET

    text = re.sub(r'<!DOCTYPE[^>]*>', '', text)  # the DTD of ChemDraw is not fetched
    try:
        return ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(tr('CDXML: файл не читается как XML ({}).').format(exc)) from None


def _cdxml_nodes(root):
    """(nodes [(id, symbol, x, y, charge)], bonds [(id1, id2, order)]) of the fragments of the first page; refused —
    an abbreviation (Ph, OMe, Boc …: a node with a fragment of its own)."""
    nodes, bonds = [], []
    page = next(iter(root.iter('page')), root)
    for fragment in page.iter('fragment'):
        for node in fragment.findall('n'):
            kind = node.get('NodeType', '')
            if node.find('fragment') is not None or kind in ('Fragment', 'Nickname', 'GenericNickname', 'Unspecified'):
                label = ''.join(t.text or '' for t in node.iter('s')).strip()
                raise ValueError(tr('CDXML: сокращение «{}» — раскройте его в ChemDraw (Expand Label) и сохраните '
                                    'заново.').format(label or kind))
            if kind == 'ExternalConnectionPoint':
                continue
            try:
                x, y = (float(v) for v in node.get('p', '').split()[:2])
            except ValueError:
                continue
            number = int(node.get('Element', '6'))
            symbol = SYMBOLS[number - 1] if 1 <= number <= len(SYMBOLS) else 'C'
            nodes.append((node.get('id'), symbol, x, y, int(float(node.get('Charge', '0') or 0))))
        for bond in fragment.findall('b'):
            order = {'1': 1, '2': 2, '3': 3, '1.5': 1.5, '0.5': 1, 'dative': 1}.get(bond.get('Order', '1'), 1)
            bonds.append((bond.get('B'), bond.get('E'), order))
    return nodes, bonds


def read_cdxml(text):
    """A ChemDraw CDXML file — the atoms of the fragments of its first page
    (Element: the atomic number, carbon when absent; p: the point on the drawing), its bonds and their orders; the
    drawing in points, y downwards — turned to Å (the mean bond 1.45 Å), y upwards, z = 0: a flat structure that
    «Сделать 3D» raises and the hydrogens complete (the implicit H of ChemDraw are not in the file)."""
    root = _cdxml_tree(text)
    nodes, bonds = _cdxml_nodes(root)
    if not nodes:
        raise ValueError(tr('CDXML: в файле нет молекулы (фрагментов с атомами).'))
    index = {ident: k for k, (ident, *_rest) in enumerate(nodes)}
    edges = [(index[a], index[b], o) for a, b, o in bonds if a in index and b in index and a != b]
    lengths = sorted(((nodes[i][2] - nodes[j][2]) ** 2 + (nodes[i][3] - nodes[j][3]) ** 2) ** 0.5 for i, j, _ in edges)
    typical = lengths[len(lengths) // 2] if lengths else 14.4  # the bond of ChemDraw: 14.4 pt
    scale = 1.45 / typical if typical > 1e-6 else 0.1
    cx = sum(n[2] for n in nodes) / len(nodes)
    cy = sum(n[3] for n in nodes) / len(nodes)
    atoms = [(symbol, (x - cx) * scale, -(y - cy) * scale, 0.0) for _, symbol, x, y, _ in nodes]
    title = ''
    for t in root.iter('t'):
        words = ''.join(s.text or '' for s in t.iter('s')).strip()
        if words and len(words) < 60:
            title = words
            break
    return _molecule(title or 'ChemDraw', atoms, edges)


def cdxml_charges(text):
    """The formal charges of the atoms of read_cdxml, in its order."""
    return [charge for *_rest, charge in _cdxml_nodes(_cdxml_tree(text))[0]]


def write_mol2(molecule, bonds):
    rows = ''.join(
        f'{k + 1:6d} {a.symbol}{k + 1:<6d} {a.x:10.4f} {a.y:10.4f} {a.z:10.4f} {a.symbol:<5} 1 MOL 0.0000\n'
        for k, a in enumerate(molecule.atoms)
    )
    links = ''.join(
        f'{k + 1:6d} {i + 1:5d} {j + 1:5d} {"ar" if o == 1.5 else int(o)}\n' for k, (i, j, o) in enumerate(bonds)
    )
    return (
        f'@<TRIPOS>MOLECULE\n{molecule.title or "MOL"}\n{len(molecule.atoms)} {len(bonds)} 1 0 0\nSMALL\nNO_CHARGES\n\n'
        f'@<TRIPOS>ATOM\n{rows}@<TRIPOS>BOND\n{links}'
    )


# -- PDB -------------------------------------------------------------------------------------------
@readable('PDB')
def read_pdb(text):
    atoms, serial, conect, title = [], {}, [], ''
    standard = set()  # the atoms of ATOM records — the PDB gives no CONECT for the bonds of standard residues
    alternate = {}  # (chain, residue, atom name) -> the altLoc kept (the first one, usually A)
    for n, line in enumerate(text.replace('\r', '').split('\n'), start=1):
        tag = line[:6].strip()
        if tag in ('ATOM', 'HETATM'):
            alt = line[16:17].strip()
            if alt:  # alternative positions of one atom: only the first set (before, both — atoms on top of each other)
                key = (line[21:27], line[17:20], line[12:16])
                if alternate.setdefault(key, alt) != alt:
                    continue
            try:
                element = pdb_element(line, tag)
                xyz = (_f(line[30:38]), _f(line[38:46]), _f(line[46:54]))
            except ValueError as exc:
                raise ValueError(tr(f'PDB, строка {n}: {exc}')) from None
            serial[line[6:11].strip()] = len(atoms)
            if tag == 'ATOM':
                standard.add(len(atoms))
            atoms.append((element, *xyz))
        elif tag == 'CONECT':
            fields = [line[k : k + 5].strip() for k in range(6, 31, 5)]
            fields = [x for x in fields if x]
            conect.extend((fields[0], x) for x in fields[1:])  # an empty CONECT gives nothing
        elif tag in ('COMPND', 'HEADER') and not title:
            title = line[10:].strip()
        elif tag in ('ENDMDL', 'END'):
            if atoms:
                break
    bonds = None
    if conect:
        count = {}
        for a, b in conect:
            if a in serial and b in serial:
                key = tuple(sorted((serial[a], serial[b])))
                count[key] = count.get(key, 0) + 1
        # each bond is listed from both ends; a double bond twice from each end
        bonds = [(i, j, min(3, max(1, (n + 1) // 2))) for (i, j), n in count.items()]
        covered = {k for i, j, _ in bonds for k in (i, j)}
        if standard - covered:  # a protein with CONECT only for S–S and ligands (1CRN: 3 bonds for 327 atoms)
            from modules.compass.chemistry.builder import connections

            listed = {(i, j): o for i, j, o in bonds}
            plain = _molecule(title or 'PDB', atoms, None)
            found = {(min(i, j), max(i, j)): 1 for i, j, _ in connections(plain)}
            if set(listed) <= set(found):  # nothing CONECT knows beyond the distances: perceive the orders as usual
                bonds = None
            else:  # long bonds (metals) of CONECT kept, with its orders
                found.update(listed)
                bonds = [(i, j, o) for (i, j), o in sorted(found.items())]
    return _molecule(title or 'PDB', atoms, bonds)


def pdb_element(line, tag='ATOM'):
    """The element of an ATOM/HETATM line: columns 77–78; without them, from the atom name by the PDB rule —
    a name that starts in column 14 (« CA ») is a one-letter element (C-alpha, not calcium), one that starts in column
    13 («CA », «FE ») a two-letter one; the hydrogens of an amino acid (« HB2», «HD21», «HG12») are H."""
    element = re.sub(r'[^A-Za-z]', '', line[76:78])
    if element:
        return _symbol(element)
    name = line[12:16]
    letters = re.sub(r'[^A-Za-z]', '', name)
    if not letters:
        raise ValueError(tr('нет ни элемента, ни имени атома.'))
    if tag == 'ATOM' and letters[0].upper() == 'H':
        return 'H'
    if name[:1] in (' ', '') or name[:1].isdigit():
        return _symbol(letters[0])
    two = letters[:2].capitalize()
    return two if two in SYMBOLS and tag == 'HETATM' else _symbol(letters[0])


AMINO = {'ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLN', 'GLU', 'GLY', 'HIS', 'ILE', 'LEU', 'LYS', 'MET', 'PHE', 'PRO',
         'SER', 'THR', 'TRP', 'TYR', 'VAL', 'SEC', 'PYL', 'HSD', 'HSE', 'HIE', 'HID', 'HIP', 'CYX', 'ASH', 'GLH'}
NUCLEIC = {'DA', 'DC', 'DG', 'DT', 'DU', 'A', 'C', 'G', 'U', 'T'}


def pdb_labels(text):
    """The residues of a PDB file as own labels of atoms {index: 'Ala12'} (chain added when there are
    several, «A:Ala12»): one label per residue, on its CA (amino acids), C1' (nucleotides) or first atom; none for a
    file of a single residue or of the generic MOL / UNL / UNK / LIG (a small molecule)."""
    residues, order, chains = {}, [], set()
    index = 0
    for line in text.replace('\r', '').split('\n'):
        tag = line[:6].strip()
        if tag in ('ATOM', 'HETATM'):
            name, residue = line[12:16].strip(), line[17:20].strip()
            chain, number = line[21:22].strip(), line[22:27].strip()
            key = (chain, number, residue)
            if key not in residues:
                residues[key] = []
                order.append(key)
            residues[key].append((index, name))
            chains.add(chain)
            index += 1
        elif tag in ('ENDMDL', 'END') and index:
            break
    real = [k for k in order if k[2] and k[2].upper() not in ('MOL', 'UNL', 'UNK', 'LIG')]
    if len(real) < 2:
        return {}
    labels = {}
    for chain, number, residue in real:
        atoms = residues[(chain, number, residue)]
        upper = residue.upper()
        where = next((i for i, n in atoms if n == ('CA' if upper in AMINO else "C1'")), atoms[0][0])
        name = residue.capitalize() if upper in AMINO else residue
        labels[where] = (f'{chain}:' if len(chains) > 1 and chain else '') + f'{name}{number}'
    return labels


def write_pdb(molecule, bonds):
    rows = ''.join(
        f'HETATM{k + 1:5d} {a.symbol + str(k + 1):<4} MOL A   1    {a.x:8.3f}{a.y:8.3f}{a.z:8.3f}  1.00  0.00          {a.symbol:>2}\n'
        for k, a in enumerate(molecule.atoms)
    )
    links = {}
    for i, j, o in bonds:
        for a, b in ((i, j), (j, i)):
            links.setdefault(a, []).extend([b] * (2 if o == 2 else 3 if o == 3 else 1))
    conect = ''.join(
        'CONECT' + f'{a + 1:5d}' + ''.join(f'{b + 1:5d}' for b in sorted(bs)) + '\n' for a, bs in sorted(links.items())
    )
    return f'COMPND    {molecule.title}\n' + rows + conect + 'END\n'


def pdb_model_count(text):
    """The number of MODEL records (frames of an MD or NMR ensemble); 1 without them."""
    return max(1, len(re.findall(r'^MODEL\b', text, re.M)))


def pdb_trajectory(text):
    """The MODEL … ENDMDL frames of a PDB file → Trajectory (no energies) for the steps drawer."""
    chunks = re.split(r'^ENDMDL[^\n]*$', text.replace('\r', ''), flags=re.M)
    frames = []
    for chunk in chunks:
        if re.search(r'^(?:ATOM|HETATM)', chunk, re.M):
            if not re.search(r'^CONECT', chunk, re.M):  # CONECT is usually written once, after the last model
                chunk += '\n' + '\n'.join(re.findall(r'^CONECT[^\n]*$', text, re.M))
            frames.append(read_pdb(chunk))
    if not frames:
        raise ValueError(tr('В файле нет атомов.'))
    steps = tuple(Step(k + 1, None, f) for k, f in enumerate(frames))
    return Trajectory(steps, frames[0], frames[-1], 'PDB')


