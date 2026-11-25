"""Compute the reference outputs of a set in tests/data/<set>/inputs with the programs installed here.

§1 PURPOSE
    A new reader (Raman, NBO, ...) is written against real outputs, not against outputs recalled from memory. The
    inputs of a set are kept in the repository; this script runs them with ORCA (*.inp), Gaussian (*.gjf, *.com) and
    MOPAC (*.mop; 0.91 — its .aux and .arc are kept too) and xtb (<name>.xcontrol with <name>.xyz and the
    arguments in <name>.args; xtbscan.log, xtbopt.log and xtbopt.xyz are kept as <name>.xtbscan.log …)
    found as Sextant finds them, and copies each output next to the inputs: tests/data/<set>/<name>.out (ORCA) or
    <name>.log (Gaussian). Only the output is kept; the other files (.gbw, .hess, .chk) stay in the temporary folder.
§2 USE
    .venv/bin/python tools/run_references.py raman [--programs orca,gaussian] [--timeout 1800] [--keep]
    (Windows: .venv\\Scripts\\python.exe tools\\run_references.py raman). An output already there is not computed
    again unless --again is given.
§3 REPORT
    For every input: the program, «нормально» (the end marker of the program) or the code, the seconds, and the
    markers the set expects (raman: «RAMAN SPECTRUM» of ORCA, «Raman Activ» of Gaussian) — found or not.
§4 ROBUSTNESS
    A program not found: its inputs are skipped and named. A timeout stops the program and says so. Outputs are read
    as UTF-8 with errors='replace'.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.sextant import runner  # noqa: E402

KINDS = {'.inp': 'orca', '.gjf': 'gaussian', '.com': 'gaussian', '.mop': 'mopac', '.xcontrol': 'xtb', '.nw': 'nwchem',
         '.in': 'qchem'}
OUTPUT = {'orca': '.out', 'gaussian': '.log', 'mopac': '.out', 'xtb': '.out', 'nwchem': '.out', 'qchem': '.out'}
EXTRA = {'mopac': ('.aux', '.arc')}  # kept next to the output too (the .aux is read by Spectrum)
END = {'orca': 'ORCA TERMINATED NORMALLY', 'gaussian': 'Normal termination', 'mopac': 'MOPAC DONE',
       'xtb': 'normal termination of xtb', 'nwchem': 'Total times  cpu:', 'qchem': 'Thank you very much for using Q-Chem'}
XTB_KEPT = ('xtbscan.log', 'xtbopt.log', 'xtbopt.xyz')  # next to the output as <name>.xtbscan.log …
MARKERS = {'raman': {'orca': ('RAMAN SPECTRUM',), 'gaussian': ('Raman Activ',)}}


def command(kind, program, inp):
    if kind == 'orca':
        return [str(program), inp.name]  # ORCA wants its full path; the output goes to stdout
    if kind == 'mopac':
        return [str(program), inp.name]  # MOPAC writes <name>.out, .aux and .arc next to the input
    if kind == 'nwchem':
        return [str(program), inp.name]  # the output goes to stdout
    if kind == 'qchem':
        return [str(program), inp.name, inp.with_suffix('.out').name]
    if kind == 'xtb':  # the geometry, the control file under its usual name, the arguments of <name>.args
        args = inp.with_suffix('.args')
        return ([str(program), inp.with_suffix('.xyz').name, '--input', 'xcontrol']
                + (args.read_text(encoding='utf-8').split() if args.exists() else []))
    return [str(program), inp.name, inp.with_suffix('.log').name]


def find_mopac():
    """0.91: MOPAC of «Установить MOPAC» (.tools/calc) or of PATH; Sextant does not know it yet."""
    names = ('mopac.exe', 'MOPAC2016.exe', 'mopac') if sys.platform == 'win32' else ('mopac', 'MOPAC2016.exe')
    for folder in (ROOT / '.tools' / 'calc' / 'bin', ROOT / '.tools' / 'calc' / 'Library' / 'bin'):
        for name in names:
            if (folder / name).is_file():
                return folder / name
    found = next((shutil.which(n) for n in names if shutil.which(n)), None)
    return Path(found) if found else None


def find_qchem():
    """Q-Chem is not a program of Sextant: the command qchem of PATH (its environment set up by Q-Chem itself)."""
    found = shutil.which('qchem')
    return Path(found) if found else None


def run_one(kind, program, source, target, timeout, markers, work):
    folder = Path(tempfile.mkdtemp(prefix=source.stem + '-', dir=work))
    inp = folder / source.name
    shutil.copyfile(source, inp)
    if kind == 'xtb':
        shutil.copyfile(source, folder / 'xcontrol')
        for suffix in ('.xyz', '.args'):
            if source.with_suffix(suffix).exists():
                shutil.copyfile(source.with_suffix(suffix), inp.with_suffix(suffix))
    env = runner.environment(program, kind, 1, folder=folder)
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    started = time.monotonic()
    try:
        if kind in ('orca', 'xtb', 'nwchem'):  # they print the output to stdout
            with open(folder / (source.stem + '.out'), 'w', encoding='utf-8', errors='replace') as out:
                code = subprocess.run(command(kind, program, inp), cwd=folder, env=env, stdout=out,
                                      stderr=subprocess.STDOUT, timeout=timeout, creationflags=flags).returncode
        else:
            code = subprocess.run(command(kind, program, inp), cwd=folder, env=env, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.STDOUT, timeout=timeout, creationflags=flags).returncode
    except subprocess.TimeoutExpired:
        return f'дольше {timeout} с', ''
    except OSError as exc:
        return f'не запустилась: {exc}', ''
    seconds = time.monotonic() - started
    produced = folder / (source.stem + OUTPUT[kind])
    if not produced.exists():
        return f'нет вывода (код {code})', ''
    text = produced.read_text(encoding='utf-8', errors='replace')
    shutil.copyfile(produced, target)
    for suffix in EXTRA.get(kind, ()):
        if (folder / (source.stem + suffix)).exists():
            shutil.copyfile(folder / (source.stem + suffix), target.with_suffix(suffix))
    if kind == 'xtb':
        for name in XTB_KEPT:
            if (folder / name).exists():
                shutil.copyfile(folder / name, target.parent / f'{source.stem}.{name}')
    status = 'нормально' if END[kind] in text else f'код {code}, без «{END[kind]}»'
    found = ', '.join(f'{m}: {"есть" if m in text else "НЕТ"}' for m in markers)
    return f'{status}, {seconds:.0f} с', found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('set', help='the folder in tests/data, e.g. raman')
    parser.add_argument('--programs', default='orca,gaussian,mopac,xtb')
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--again', action='store_true', help='compute outputs that are already there')
    parser.add_argument('--keep', action='store_true', help='keep the temporary folders')
    args = parser.parse_args(argv)
    base = ROOT / 'tests' / 'data' / args.set
    inputs = sorted(p for p in (base / 'inputs').iterdir() if p.suffix in KINDS) if (base / 'inputs').is_dir() else []
    if not inputs:
        print(f'Нет входных файлов в {base / "inputs"}')
        return 1
    wanted = {k.strip() for k in args.programs.split(',') if k.strip()}
    programs = {kind: find_mopac() if kind == 'mopac' else find_qchem() if kind == 'qchem' else runner.find_program(kind)
                for kind in wanted}
    work = Path(tempfile.mkdtemp(prefix='azimuth-references-'))
    failed = 0
    for source in inputs:
        kind = KINDS[source.suffix]
        if kind not in wanted:
            continue
        target = base / (source.stem + OUTPUT[kind])
        if programs[kind] is None:
            print(f'  пропущен   {source.name} — {kind} не найдена', flush=True)
            continue
        if target.exists() and not args.again:
            print(f'  уже есть   {target.name}', flush=True)
            continue
        print(f'  считается  {source.name} ({programs[kind]}) …', flush=True)
        status, found = run_one(kind, programs[kind], source, target, args.timeout,
                                MARKERS.get(args.set, {}).get(kind, ()), work)
        failed += not status.startswith('нормально') or 'НЕТ' in found
        print(f'             {status}' + (f'; {found}' if found else ''), flush=True)
    if args.keep:
        print(f'\nВременные папки: {work}')
    else:
        shutil.rmtree(work, ignore_errors=True)
    print(f'\nВыводы: {base}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
