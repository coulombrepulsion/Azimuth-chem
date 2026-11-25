"""Run by a Python with RDKit (not imported by Azimuth): 3D coordinates for the records of an SDF.

    python -I rdkit_embed.py in.sdf out.sdf [conformers]

Every record keeps its atoms, their order and its explicit hydrogens (no implicit hydrogens are added: the atom count
is the one Azimuth wrote); ETKDGv3, the lowest of N conformers after MMFF94 (UFF when MMFF has no parameters; no force
field when the record cannot be sanitized — then the ETKDG geometry). A record that cannot be embedded is written as it
came with the data item «Azimuth3D» = «failed: …»; one written in 3D — «ok: <field>». Standard library and RDKit only.
«k n» on the standard output before every record (k done of n) — the progress Azimuth shows.
"""

import sys

from rdkit import Chem
from rdkit.Chem import AllChem


def embed(mol, count, seed=0xA21):
    for atom in mol.GetAtoms():
        atom.SetNoImplicit(True)
    try:
        Chem.SanitizeMol(mol)
        clean = True
    except Exception:  # noqa: BLE001 — an unusual valence: the geometry only
        mol.UpdatePropertyCache(strict=False)
        Chem.GetSymmSSSR(mol)
        clean = False
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    ids = list(AllChem.EmbedMultipleConfs(mol, numConfs=count, params=params))
    if not ids:
        params.useRandomCoords = True
        ids = list(AllChem.EmbedMultipleConfs(mol, numConfs=count, params=params))
    if not ids:
        raise ValueError('ETKDG did not embed it')
    field, energies = 'ETKDG', [0.0] * len(ids)
    if clean and AllChem.MMFFHasAllMoleculeParams(mol):
        field, results = 'MMFF94', AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=2000)
        energies = [e + (1e6 if c else 0.0) for c, e in results]
    elif clean and AllChem.UFFHasAllMoleculeParams(mol):
        field, results = 'UFF', AllChem.UFFOptimizeMoleculeConfs(mol, maxIters=2000)
        energies = [e + (1e6 if c else 0.0) for c, e in results]
    best = ids[min(range(len(ids)), key=energies.__getitem__)]
    keep = Chem.Conformer(mol.GetConformer(best))
    mol.RemoveAllConformers()
    mol.AddConformer(keep, assignId=True)
    return field


def main(source, target, count):
    blocks = [b for b in open(source, encoding='utf-8').read().split('$$$$\n') if b.strip()]
    with open(target, 'w', encoding='utf-8') as out:
        for number, block in enumerate(blocks):
            print(f'{number} {len(blocks)}', flush=True)  # the progress, read by embed3d.run
            mol = Chem.MolFromMolBlock(block, removeHs=False, sanitize=False)
            status = 'failed: not read by RDKit'
            if mol is not None:
                atoms = mol.GetNumAtoms()
                try:
                    status = 'ok: ' + (embed(mol, count) if atoms > 1 else 'one atom')
                    if mol.GetNumAtoms() != atoms:
                        raise ValueError('the number of atoms changed')
                    block = Chem.MolToMolBlock(mol, kekulize=False)
                except Exception as exc:  # noqa: BLE001 — the record as it came, with the reason
                    status = f'failed: {exc}'.replace('\n', ' ')[:200]
            head = block.split('M  END')[0].rstrip('\n')
            out.write(head + '\nM  END\n>  <Azimuth3D>\n' + status + '\n\n$$$$\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 20)
