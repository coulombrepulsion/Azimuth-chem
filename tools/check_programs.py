"""Run the input files Sextant writes on the programs installed here: a short calculation for every task and the main
options, on a small molecule; the table says which ran to a normal end and Spectrum read the result.

§1 PURPOSE
    The keywords of ORCA 6, Gaussian 16 and Psi4 in modules/sextant/inputs.py and the checks of input_check.py were
    written from memory of the manuals (ASSUMPTION there). Before the beta every input Sextant writes is run by the
    real program: «normal end» (the marker of the program), the code, what diagnose() recognised, and what
    modules.spectrum.readers.outputs.read_any read (the energy, the steps, the frequencies, the states, the shieldings).
§2 USE
    .venv/bin/python tools/check_programs.py [--programs orca,xtb] [--quick] [--cores 1] [--keep] [--failures |
    --only-failures] (ORCA made to fail on purpose — the SCF, the optimization, the memory, a wrong keyword,
    the multiplicity — is the message of Sextant the right one?)
    (Windows: .venv\\Scripts\\python.exe tools\\check_programs.py). The programs are found as Sextant finds them; the
    calculations run in a temporary folder (with --keep in Documents/Azimuth/check-<date>); the table is printed
    and written to check_programs_<date>.md next to the program folder.
§3 CASES
    Water, HF-3c-like small settings (B3LYP/def2-SVP by default; xtb: GFN2): energy, optimization, optimization +
    frequencies, UV-Vis (TD-DFT, 3 states), NMR, excited-state optimization (root 1), the solvent (water), D3BJ and D4,
    the tight convergence, the populations, a frozen distance (constraints of Compass), an edited keyword (extra).
    --quick: energy, optimization + frequencies, UV-Vis only.
    --beta (before the beta): the ASSUMPTIONs of 0.89–0.91 that only a run of the real program closes — ORCA: SMD
    (water), the stability analysis (stretched H2, RHF → UHF), the NTO of TD-DFT (the .nto read by orca_2mkl as a .gbw),
    the start from the orbitals of a previous run (MORead), the TMS reference of NMR at the level of the water result,
    the excited-state optimization with «! LibXC(B3LYP)»; MOPAC: the methyl radical (RHF open shell, «SINGLY OCCUPIED»).
    --beta --programs multiwfn: the analyses of Spectrum and Compass from ORCA wavefunctions written here, end to end
    (ORCA → orca_2mkl → Multiwfn → the parser): Hirshfeld, RESP, LMO, LI/DI and DOS of water, Fukui (water N, N + 1,
    N − 1), IFCT of the S1 of formaldehyde (C=O → H2), CDA of H3N→BH3. --beta --programs crest: butane-1,4-diol with
    and without «--mdlen x2» (the ASSUMPTION of the longer metadynamics finds more conformers). Ethylene glycol
    (the first try) gave one conformer either way (CREST 3, GFN2): too rigid to tell.
"""

import argparse
import sys
import tempfile
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from azimuth.core import Calculation, read_xyz  # noqa: E402
from modules.sextant import runner  # noqa: E402

WATER = read_xyz('3\nwater\nO 0.000 0.000 0.117\nH 0.000 0.757 -0.467\nH 0.000 -0.757 -0.467\n')
# the first excited state of water dissociates (n → σ*): its optimization never converges (ORCA 6.0.1, 100 cycles);
# formaldehyde has a bound S1 (n → π*, pyramidal) — the case of the excited-state optimization
FORMALDEHYDE = read_xyz('4\nformaldehyde\nC 0.000 0.000 -0.529\nO 0.000 0.000 0.677\nH 0.000 0.937 -1.115\nH 0.000 -0.937 -1.115\n')
OPTIMIZATIONS = ('Оптимизация', 'Оптимизация + частоты', 'Оптимизация возбуждённого состояния (TD-DFT)')
END = {'orca': 'ORCA TERMINATED NORMALLY', 'gaussian': 'Normal termination', 'psi4': '*** Psi4 exiting successfully',
       'xtb': 'normal termination of xtb'}
BASE = Calculation(method='B3LYP', basis='def2-SVP', task='Энергия', cores=1, memory_mb=500)


def cases(kind, quick):
    tasks = ['Энергия', 'Оптимизация', 'Оптимизация + частоты', 'Спектр UV-Vis (TD-DFT)', 'ЯМР (экранирование)',
             'Оптимизация возбуждённого состояния (TD-DFT)']
    if kind == 'xtb':
        tasks = ['Энергия', 'Оптимизация', 'Оптимизация + частоты']
    if quick:
        tasks = [t for t in tasks if t in ('Энергия', 'Оптимизация + частоты', 'Спектр UV-Vis (TD-DFT)')]
    out = [(task, {}, ()) for task in tasks]
    if not quick:
        out += [
            ('Энергия', {'solvent': 'water'}, ()),
            ('Энергия', {'dispersion': 'D3BJ'}, ()),
            ('Энергия', {'dispersion': 'D4'}, ()),
            ('Энергия', {'scf': 'verytight', 'population': 'hirshfeld'}, ()),
            ('Оптимизация', {}, (('B', (0, 1)),)),  # a frozen O–H distance from Compass
        ]
        if kind == 'orca':
            out += [('Энергия', {'rijcosx': True}, ()), ('Энергия', {'relativistic': 'ZORA', 'basis': 'def2-SVP'}, ()),
                    ('Спектр UV-Vis (TD-DFT)', {'tddft_mode': 'tda', 'triplets': True}, ())]
    return out


def run_case(kind, program, task, options, constraints, root, cores, timeout):
    calc = replace(BASE, task=task, cores=cores, states=3, **options)
    if kind == 'xtb':
        calc = replace(calc, dispersion='')
    label = task + ''.join(f', {k}={v}' for k, v in options.items()) + (', ограничение' if constraints else '')
    mpirun = runner.find_mpirun(program) if kind == 'orca' and cores > 1 else None
    try:
        molecule = FORMALDEHYDE if task == 'Оптимизация возбуждённого состояния (TD-DFT)' else WATER
        spec = runner.prepare(kind, program, molecule, calc, constraints, root, mpirun=mpirun)
    except ValueError as exc:
        return label, 'не записан', str(exc)
    job = runner.Job(spec).start()
    start = time.monotonic()
    while job.poll() is None:
        if time.monotonic() - start > timeout:
            job.stop()
            return label, 'не дождался', f'{timeout} с'
        time.sleep(0.5)
    text = spec.output.read_text(encoding='utf-8', errors='replace') if spec.output.is_file() else ''
    ended = END[kind] in text
    problems = '; '.join(what for what, _ in runner.diagnose(kind, text, job.code)) if not ended else ''
    read = ''
    try:
        from modules.spectrum.readers.outputs import read_any

        result = read_any(text, spec.output)
        parts = []
        if getattr(result, 'energies', None):
            parts.append(f'E {result.energies[-1]:.6f}')
        if getattr(result, 'optimization_converged', False):
            parts.append('сошлась')
        for name, short in (('steps', 'шагов'), ('frequencies', 'частот'), ('absorption', 'состояний'),
                            ('shieldings', 'ЯМР')):
            value = getattr(result, name, None)
            if value:
                parts.append(f'{short} {len(value)}')
        read = ', '.join(parts) or 'прочитан'
    except Exception as exc:  # noqa: BLE001 — the report says it
        read = f'не прочитан: {exc}'[:80]
    status = 'ok' if ended and job.code == 0 else f'код {job.code}'
    if status == 'ok' and task in OPTIMIZATIONS and 'сошлась' not in read:
        status = 'не сошлась'  # the program ended normally, but the geometry did not converge
    return label, status, (problems + ' · ' if problems else '') + read + f' · {time.monotonic() - start:.0f} с · {spec.folder.name}'


# failures on purpose — does runner.diagnose say what went wrong? (label, molecule, task, edit of the ORCA
# input, the start of the message expected); the edits make the real programs fail the way users meet it
STRETCHED = read_xyz('3\nwater\nO 0.000 0.000 0.117\nH 0.000 1.300 -0.900\nH 0.000 -0.700 -0.400\n')


def failure_cases(kind):
    if kind != 'orca':
        return []

    def block(text, line):
        return text.replace('%maxcore', line + '\n%maxcore', 1)

    return [
        ('SCF за 3 итерации', WATER, 'Энергия', {}, lambda t: block(t, '%scf MaxIter 3 end'), 'Самосогласованное поле'),
        ('оптимизация за 2 шага', STRETCHED, 'Оптимизация', {}, lambda t: block(t, '%geom MaxIter 2 end'), 'Оптимизация геометрии'),
        ('память 1 МБ', WATER, 'Оптимизация + частоты', {}, lambda t: t.replace('%maxcore 500', '%maxcore 1'), 'Не хватило памяти'),
        ('неизвестное слово', WATER, 'Энергия', {}, lambda t: t.replace('TightSCF', 'TightSCF FooBarKeyword', 1), 'Ошибка во входном'),
        ('мультиплетность 2 у воды', WATER, 'Энергия', {}, lambda t: t.replace('* xyz 0 1', '* xyz 0 2'), 'Заряд и мультиплетность'),
    ]


def run_failure(kind, program, case, root, timeout):
    from modules.sextant import inputs

    label, molecule, task, options, edit, expected = case
    calc = replace(BASE, task=task, **options)
    try:
        text = inputs.preview(kind, molecule, calc, ())
        spec = runner.prepare(kind, program, molecule, calc, (), root, text=edit(text) if edit else None)
    except ValueError as exc:
        return label, 'не записан', str(exc)
    job = runner.Job(spec).start()
    start = time.monotonic()
    while job.poll() is None:
        if time.monotonic() - start > timeout:
            job.stop()
            return label, 'не дождался', f'{timeout} с'
        time.sleep(0.5)
    out = spec.output.read_text(encoding='utf-8', errors='replace') if spec.output.is_file() else ''
    found = [what for what, _ in runner.diagnose(kind, out, job.code)]
    if found and found[0].startswith(expected):
        return label, 'узнал', found[0]
    tail = ' / '.join(line.strip() for line in out.strip().splitlines()[-4:] if line.strip())[:300]
    return label, 'не узнал', (f'сказано: {found[0]} · ' if found else '') + f'код {job.code} · конец вывода: {tail}'


# the checks of the ASSUMPTIONs before the beta (§3 --beta); H2 stretched to 1.6 A has an RHF → UHF instability
H2_STRETCHED = read_xyz('2\nH2\nH 0 0 0\nH 0 0 1.6\n')
METHYL = read_xyz('4\nmethyl\nC 0 0 0\nH 1.079 0 0\nH -0.5395 0.9344 0\nH -0.5395 -0.9344 0\n')


def _run(kind, program, molecule, calc, root, timeout, text=None):
    """(spec, job code, output text) of one calculation, or (None, None, message) when it is not written."""
    try:
        spec = runner.prepare(kind, program, molecule, calc, (), root, text=text)
        job = runner.Job(spec).start()
    except ValueError as exc:
        return None, None, str(exc)
    start = time.monotonic()
    while job.poll() is None:
        if time.monotonic() - start > timeout:
            job.stop()
            return spec, None, f'не дождался {timeout} с'
        time.sleep(0.5)
    text = spec.output.read_text(encoding='utf-8', errors='replace') if spec.output.is_file() else ''
    return spec, job.code, text


# H3N→BH3 (C3v, staggered): N–B 1.658, N–H 1.018, B–H 1.216 A, H–N–B 107.0°, N–B–H 104.6° — the donor NH3 first
def _ammonia_borane():
    from math import cos, radians, sin

    atoms = ['N 0 0 0']
    for k in range(3):
        f = radians(120 * k)
        atoms.append(f'H {0.9735 * cos(f):.4f} {0.9735 * sin(f):.4f} -0.2977')
    atoms.append('B 0 0 1.658')
    for k in range(3):
        f = radians(120 * k + 60)
        atoms.append(f'H {1.1767 * cos(f):.4f} {1.1767 * sin(f):.4f} {1.658 + 0.3066:.4f}')
    return read_xyz(f'{len(atoms)}\nH3N-BH3\n' + '\n'.join(atoms) + '\n')


def multiwfn_checks(program, root, timeout):
    """The analyses of §3 (--programs multiwfn): [(label, status, note)]."""
    from modules.spectrum.analysis import charge_transfer, delocalization, dos, fukui
    from modules.spectrum.wavefunction import multiwfn_cda, multiwfn_lmo, multiwfn_populations, multiwfn_resp
    from modules.spectrum.readers.orbital_files import read_molden

    orca = runner.find_program('orca')
    if orca is None:
        return [('Multiwfn', 'нет ORCA', 'волновые функции считает ORCA')]
    out = []

    def wavefunction(molecule, calc, label):
        spec, code, text = _run('orca', orca, molecule, calc, root, timeout)
        if code is None or not runner.finished_normally('orca', text, code):
            raise ValueError(f'{label}: ORCA ' + (text[-200:] if spec is None else f'код {code}'))
        return runner.molden_from_gbw(spec.output.with_suffix('.gbw'), orca), spec, text

    def check(label, work):
        try:
            out.append((label, 'ok', work()))
        except (ValueError, OSError, KeyError, IndexError, InterruptedError) as exc:
            out.append((label, 'сбой', str(exc)[:300]))

    energy = replace(BASE, task='Энергия')
    try:
        water, _, _ = wavefunction(WATER, energy, 'вода')
    except ValueError as exc:
        return [('Multiwfn: вода', 'сбой', str(exc))]

    def hirshfeld():
        charges, _ = multiwfn_populations.run_hirshfeld(program, water)
        return 'q ' + ', '.join(f'{q:+.4f}' for q in charges)

    def resp():
        charges, rmse, rrmse, chg, _ = multiwfn_resp.run_resp(program, water)
        return 'q ' + ', '.join(f'{q:+.4f}' for q in charges) + f'; RRMSE {rrmse:.4f}; .chg {"есть" if chg else "нет"}'

    def lmo():
        from collections import Counter

        _, summary, _ = multiwfn_lmo.run_lmo(program, water, 'pm')  # {(spin, number): (kind, shares)}
        kinds = Counter(kind for kind, _ in summary.values())
        return f'LMO {len(summary)}: ' + ', '.join(f'{k} {n}' for k, n in sorted(kinds.items()))

    def lidi():
        found, _ = delocalization.run_lidi(program, water)
        return f'DI(O,H) {found["di"][0][1]:.4f}, LI(O) {found["li"][0]:.4f}'

    def density_of_states():
        orbital_set = read_molden(Path(water).read_text(encoding='utf-8', errors='replace'))
        found = dos.curves(orbital_set, dos.by_element(WATER))
        return f'ВЗМО {found["homo"]:.2f} эВ; PDOS: {len(found["parts"])} элемента; уровней {len(found["levels"])}'

    for label, work in (('Хиршфельд (вода)', hirshfeld), ('RESP (вода)', resp), ('LMO Пипек — Меззи (вода)', lmo),
                        ('LI/DI (вода)', lidi), ('DOS/PDOS (вода)', density_of_states)):
        check(label, work)

    def fukui_indices():
        paths = {'n': water}
        for key, charge, mult in (('anion', -1, 2), ('cation', 1, 2)):
            paths[key], _, _ = wavefunction(WATER, replace(energy, charge=charge, multiplicity=mult), key)
        charges, _ = fukui.run(program, paths)
        values = fukui.condensed(charges['n'], charges['anion'], charges['cation'])
        return f'f⁺(O) {values["plus"][0]:.4f}, f⁻(O) {values["minus"][0]:.4f}, f⁰(O) {values["zero"][0]:.4f}'

    check('Фукуи (вода N, N+1, N−1)', fukui_indices)

    def ifct():
        molden, spec, text = wavefunction(FORMALDEHYDE, replace(BASE, task='Спектр UV-Vis (TD-DFT)', states=3), 'формальдегид')
        found, _ = charge_transfer.run_ifct(program, molden, spec.output, 1, [[1, 2], [3, 4]])
        return f'S1: перенос {found["ct"]:.1f} %, локальное {found["le"]:.1f} %; дырка {found["hole"]}, электрон {found["electron"]}'

    check('IFCT S1 формальдегида (C=O → H2)', ifct)

    def cda():
        molecule = _ammonia_borane()
        donor = type(molecule)(molecule.title + ' 1', molecule.atoms[:4])
        acceptor = type(molecule)(molecule.title + ' 2', molecule.atoms[4:])
        files = [wavefunction(m, energy, name)[0] for m, name in ((molecule, 'комплекс'), (donor, 'NH3'), (acceptor, 'BH3'))]
        found, _ = multiwfn_cda.run_cda(program, files[0], files[1:])
        total = found['sum']
        return (f'd {total["d"]:.3f}, b {total["b"]:.3f}, r {total["r"]:.3f} (запись 2026.7.15 на геометрии ORCA: '
                'd 0,268, b 0,015, r −0,257)')

    check('CDA H3N→BH3', cda)
    return out


def crest_checks(program, root, timeout):
    """Butane-1,4-diol by CREST with and without «--mdlen x2» (§3): the number of conformers of each run; «окно 0»
    when CREGEN sorted with an energy window of 0 (CREST 3.0.2 on macOS), «один» for a single conformer."""
    from modules.compass.chemistry.formats import from_smiles

    molecule = from_smiles('OCCCCO')
    out = []
    for mdlen in (1.0, 2.0):
        calc = Calculation(task='Оптимизация', cores=1)  # as the window «Поиск конформеров» (conformer_actions)
        try:
            spec = runner.prepare('crest', program, molecule, calc, (), root, crest={'mdlen': mdlen})
            job = runner.Job(spec).start()
        except ValueError as exc:
            out.append((f'CREST mdlen x{mdlen:g}', 'не записан', str(exc)))
            continue
        start = time.monotonic()
        while job.poll() is None:
            if time.monotonic() - start > timeout:
                job.stop()
                break
            time.sleep(1)
        found = spec.folder / 'crest_conformers.xyz'
        if not found.is_file():
            out.append((f'CREST mdlen x{mdlen:g}', f'код {job.code}', 'нет crest_conformers.xyz'))
            continue
        lines = found.read_text(encoding='utf-8', errors='replace').splitlines()
        count, k = 0, 0
        while k < len(lines) and lines[k].strip().isdigit():
            count += 1
            k += int(lines[k]) + 2
        text = ''
        for path in (spec.output, spec.stdout):  # CREST 3.0.2 on macOS sorts with a window of 0 (crest#431)
            try:
                text += Path(path).read_text(encoding='utf-8', errors='replace')
            except (OSError, TypeError):
                pass
        status = 'окно 0' if runner.crest_window_broken(text) else 'ok' if count > 1 else 'один'
        out.append((f'CREST mdlen x{mdlen:g}', status, f'конформеров {count} · {time.monotonic() - start:.0f} с · {spec.folder.name}'
                    + (' · CREGEN с окном 0 ккал/моль — CREST 3.0.2 на macOS, crest-lab/crest#431; нужен 2.12'
                       if status == 'окно 0' else '')))
    return out


def beta_checks(kind, program, root, timeout):
    """[(label, status, note)] of the checks of §3 --beta for this program."""
    from modules.sextant import inputs
    from modules.spectrum.readers.outputs import read_any

    out = []

    def ended(code, text):
        return code is not None and runner.finished_normally(kind, text, code)

    def failed(label, spec, code, text):
        problems = '; '.join(what for what, _ in runner.diagnose(kind, text, code)) if spec is not None else ''
        tail = ' / '.join(line.strip() for line in text.strip().splitlines()[-3:] if line.strip())[:240]
        out.append((label, 'сбой' if spec is not None else 'не записан', (problems + ' · ' if problems else '') + tail))

    if kind == 'orca':
        energy = replace(BASE, task='Энергия')
        spec, code, text = _run(kind, program, WATER, replace(energy, solvent='water', solvent_model='smd'), root, timeout)
        if ended(code, text):
            out.append(('SMD (вода)', 'ok' if 'SMD' in text.upper() else 'нет SMD в выводе',
                        f'E {read_any(text).energies[-1]:.6f}; ' + ('SMD CDS' if 'CDS' in text else 'без строки CDS')))
        else:
            failed('SMD (вода)', spec, code, text)
        spec, code, text = _run(kind, program, H2_STRETCHED, replace(energy, stability=True), root, timeout)
        if ended(code, text):
            unstable = 'unstable' in text.lower() or 'UHF' in text
            out.append(('Устойчивость (H2 1,6 Å)', 'ok', ('найдена неустойчивость RHF → UHF' if unstable else
                                                          'неустойчивость не найдена') + f' · {spec.folder.name}'))
        else:
            failed('Устойчивость (H2 1,6 Å)', spec, code, text)
        spec, code, text = _run(kind, program, FORMALDEHYDE, replace(BASE, task='Спектр UV-Vis (TD-DFT)', states=3, nto=True),
                                root, timeout)
        if ended(code, text):
            nto = sorted(spec.folder.glob('*.nto'))
            note = ', '.join(p.name for p in nto) or 'файлов .nto нет'
            if nto:
                import shutil

                copy = nto[0].with_suffix('.nto.gbw')
                shutil.copy(nto[0], copy)
                try:
                    runner.molden_from_gbw(copy, program)
                    note += ' · orca_2mkl прочитал .nto как .gbw'
                except ValueError as exc:
                    note += f' · orca_2mkl: {exc}'
            out.append(('NTO (TD-DFT)', 'ok' if nto else 'нет .nto', note))
        else:
            failed('NTO (TD-DFT)', spec, code, text)
        spec, code, text = _run(kind, program, WATER, energy, root, timeout)
        gbw = spec.output.with_suffix('.gbw') if spec is not None else None
        if ended(code, text) and gbw is not None and gbw.is_file():
            spec2, code2, text2 = _run(kind, program, WATER, replace(energy, guess=str(gbw)), root, timeout)
            if ended(code2, text2):
                used = 'MOREAD' in text2.upper() and 'GBW' in text2.upper()
                cycles = [line for line in text2.splitlines() if 'SCF CONVERGED AFTER' in line]
                out.append(('Старт с орбиталей (MORead)', 'ok' if used else 'MORead не виден',
                            (cycles[-1].strip() if cycles else '') + f' · {spec2.folder.name}'))
            else:
                failed('Старт с орбиталей (MORead)', spec2, code2, text2)
        else:
            failed('Старт с орбиталей (MORead)', spec, code, text)
        spec, code, text = _run(kind, program, WATER, replace(BASE, task='ЯМР (экранирование)'), root, timeout)
        if ended(code, text):
            from modules.spectrum.analysis.nmr_reference import averaged, is_tms, tms_input, tms_molecule

            _, tms_text = tms_input(text, 'ORCA')
            spec2, code2, text2 = _run(kind, program, tms_molecule(), replace(BASE, task='ЯМР (экранирование)'), root,
                                       timeout, text=tms_text)
            if ended(code2, text2):
                tms = read_any(text2)
                ref = averaged(tms.shieldings)
                water_h = [s.isotropic for s in read_any(text).shieldings if s.element == 'H']
                delta = ref.get('H', 0) - sum(water_h) / len(water_h) if water_h and 'H' in ref else None
                out.append(('Опора TMS (ЯМР)', 'ok' if is_tms(tms.geometry) and delta is not None else 'не TMS',
                            f'σ(H) TMS {ref.get("H", 0):.3f}, σ(C) {ref.get("C", 0):.3f}; δ(H) воды '
                            + ('—' if delta is None else f'{delta:.2f}') + ' м.д.'))
            else:
                failed('Опора TMS (ЯМР)', spec2, code2, text2)
        else:
            failed('Опора TMS (ЯМР)', spec, code, text)
        for dispersion in ('', 'D3BJ'):  # D3BJ: does ORCA know the parameters of B3LYP under its LibXC name?
            label = 'LibXC(B3LYP), возбуждённое' + (', D3BJ' if dispersion else '')
            excited = replace(BASE, task='Оптимизация возбуждённого состояния (TD-DFT)', states=3, dispersion=dispersion)
            try:
                libxc = inputs.preview(kind, FORMALDEHYDE, excited, ()).replace('! B3LYP ', '! LibXC(B3LYP) ', 1)
            except ValueError as exc:
                out.append((label, 'не записан', str(exc)))
                continue
            spec, code, text = _run(kind, program, FORMALDEHYDE, excited, root, timeout, text=libxc)
            if ended(code, text):
                result = read_any(text)
                d3 = [line.strip() for line in text.splitlines() if 'Dispersion correction' in line][-1:]
                out.append((label, 'ok' if result.optimization_converged else 'не сошлась',
                            f'шагов {len(result.steps)}, E(tot) {result.energies[-1]:.6f}' + (f'; {d3[0]}' if d3 else '')))
            else:
                failed(label, spec, code, text)
    if kind == 'mopac':
        # Sextant writes «PM7 DOUBLET UHF 1SCF AUX»; the RHF open shell of a user's file (the ASSUMPTION of read by
        # «SINGLY OCCUPIED») needs the keyword RHF — MOPAC 23.2.5 without UHF still ran «UHF CALCULATION»
        calc = replace(BASE, method='PM7', task='Энергия', multiplicity=2)
        rhf = inputs.preview(kind, METHYL, calc, ()).replace(' UHF ', ' RHF ', 1)
        spec, code, text = _run(kind, program, METHYL, calc, root, timeout, text=rhf)
        if ended(code, text):
            aux = spec.output.with_suffix('.aux')
            words = [w for w in ('SINGLY OCCUPIED', 'DOUBLET', 'ROHF', 'UHF') if w in text.upper()]
            try:
                result = read_any(text, spec.output)
                note = f'прочитан; слова: {", ".join(words) or "—"}; .aux {"есть" if aux.is_file() else "нет"}'
            except ValueError as exc:
                note = f'не прочитан: {exc}'
            out.append(('Радикал CH3 (PM7, дублет)', 'ok' if 'SINGLY OCCUPIED' in text.upper() else 'нет SINGLY OCCUPIED',
                        note))
        else:
            failed('Радикал CH3 (PM7, дублет)', spec, code, text)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--programs', default='orca,xtb,gaussian,psi4')
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--cores', type=int, default=1)
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--keep', action='store_true')
    parser.add_argument('--failures', action='store_true', help='also the failures on purpose (ORCA): is the error recognised?')
    parser.add_argument('--only-failures', action='store_true', help='the failures on purpose only')
    parser.add_argument('--beta', action='store_true', help='only the checks of the ASSUMPTIONs before the beta (2026-11-07)')
    args = parser.parse_args(argv)
    stamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    root = (runner.default_jobs_root().parent / f'check-{stamp}') if args.keep else Path(tempfile.mkdtemp(prefix='azimuth-check-'))
    lines = [f'# Проверка входных файлов Секстанта · {stamp}', '']
    for kind in [k.strip() for k in args.programs.split(',') if k.strip()]:
        if kind == 'multiwfn':  # the analyses of --beta (Multiwfn is found as in the program)
            from modules.spectrum.wavefunction import multiwfn

            program = multiwfn.find()
        else:
            program = runner.find_program(kind)
        if program is None:
            lines += [f'## {kind}: не найдена', '']
            print(f'{kind}: не найдена', flush=True)
            continue
        lines += [f'## {kind}: {program}', '', '| Задача | Итог | Что прочитано |', '|---|---|---|']
        print(f'{kind}: {program}', flush=True)
        args.failures = args.failures or args.only_failures
        if args.beta:
            checks = (multiwfn_checks(program, root, args.timeout) if kind == 'multiwfn' else
                      crest_checks(program, root, args.timeout) if kind == 'crest' else
                      beta_checks(kind, program, root, args.timeout))
            for label, status, note in checks:
                print(f'  {status:12} {label} — {note}', flush=True)
                lines.append(f'| {label} | {status} | {note} |')
            lines.append('')
            continue
        for task, options, constraints in ([] if args.only_failures else cases(kind, args.quick)):
            label, status, note = run_case(kind, program, task, options, constraints, root, args.cores, args.timeout)
            print(f'  {status:12} {label} — {note}', flush=True)
            lines.append(f'| {label} | {status} | {note} |')
        if args.failures:
            for case in failure_cases(kind):
                label, status, note = run_failure(kind, program, case, root, args.timeout)
                print(f'  {status:12} ошибка: {label} — {note}', flush=True)
                lines.append(f'| ошибка: {label} | {status} | {note} |')
        lines.append('')
    report = ROOT.parent / f'check_programs_{stamp}.md'
    try:
        report.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'\nОтчёт: {report}' + (f'\nРасчёты: {root}' if args.keep else ''))
    except OSError:
        print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
