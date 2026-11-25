"""The model of a read result, shared by the readers of all programs (was in orca.py — the audit of
2026-11-04, R6: «the general model lives inside the ORCA parser»).

§1 PURPOSE
    Output — what Spectrum knows about one output of any program (ORCA, Gaussian, xtb, Psi4, NWChem, Q-Chem, GAMESS,
    MOPAC …): termination, convergence, energies, frequencies, geometries, properties; OptimizationStep — one cycle of
    an optimization. Missing evidence is kept distinct from success. The readers (orca.py, gaussian.py …) build them;
    modules/spectrum/readers/outputs.read_any chooses the reader. orca.py re-exports the names for the old imports.
§4 SPECIFICATION
    MAX_BYTES, too_large(), NUMBER, number(text), OptimizationStep, Output (.termination_status, .imaginary,
    .assessment).
§7 TESTS tests/spectrum/test_outputs.py, tests/spectrum/test_results_model.py.
"""

from dataclasses import dataclass

from azimuth.core import Molecule
from azimuth.i18n import tr

# the largest output Spectrum reads. Measured on real outputs:
# Firefly 102 MB — 2.8 s, 323 MB of memory; Gaussian 09 17 MB — 1.6 s. The text is kept with the result of its tab,
# so 256 MB is about 0.8 GB of memory per such tab (ASSUMPTION: enough for a laptop with 8 GB).
MAX_BYTES = 256_000_000


def too_large():
    return ValueError(tr('Выходной файл больше 256 МБ — Спектр такие не открывает. Откройте файл одного задания '
                         'или уменьшите печать (например, без печати орбиталей на каждом шаге).'))


NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?'


def number(text):
    return float(text.replace('D', 'E').replace('d', 'e'))


@dataclass(frozen=True)
class OptimizationStep:
    cycle: int
    energy: float | None
    geometry: Molecule | None
    gradient: tuple | None = None  # ((gx, gy, gz), ...) hartree/bohr at this geometry (ORCA)


@dataclass(frozen=True)
class Output:
    normal_exit: bool
    optimization_converged: bool
    scf_failed: bool
    energies: tuple[float, ...]
    frequencies: tuple[tuple[int, float], ...]
    geometry: Molecule | None
    demo: bool
    steps: tuple[OptimizationStep, ...] = ()
    vibration_geometry: Molecule | None = None
    modes: tuple = ()
    error_module: str | None = None
    mpi_cpu_error: bool = False
    initial_geometry: Molecule | None = None  # the echoed input
    properties: object = None  # orca_properties.Properties of the final geometry, or None
    scan: object = None  # orca_scan.Scan of a surface scan or an IRC, or None
    absorption: tuple = ()  # orca_spectra.Excitation of the electronic spectrum
    shieldings: tuple = ()  # orca_spectra.Shielding, NMR
    program: str = 'ORCA'  # also 'Gaussian 16', 'xtb 6.6.1', 'Psi4 1.7' (modules/spectrum/readers/outputs.py)
    final_energy: tuple | None = None  # (method, hartree) when the last energy is correlated (Gaussian archive)
    excited_energy: tuple | None = None  # (root, hartree) — E(tot) of the followed state of a TD-DFT single point
    raman_skipped: bool = False  # ORCA was asked for Raman with analytic frequencies and computed none
    heat_of_formation: float | None = None  # MOPAC ΔHf, kcal/mol (energies stay empty: not a total energy)
    notes: tuple = ()  # what the reader of the program has to say about the result (first in the assessment)
    mopac_thermo: tuple = ()  # MOPAC THERMO, rows (T K, ΔHf kcal/mol, H cal/mol, Cp, S cal/(K·mol)) of «TOT.»
    couplings: tuple = ()  # NMR spin-spin couplings (i, j, J Hz) — orca_spectra.read_couplings

    @property
    def termination_status(self):
        if self.error_module:
            return tr('аварийное (') + self.error_module + ')'
        return tr('нормальное') if self.normal_exit else tr('не подтверждено')

    @property
    def imaginary(self):
        return tuple((i, f) for i, f in self.frequencies if f < 0)

    @property
    def facts(self):
        """The raw facts of the output as codes — what is, and is not, in the file. The
        assessment below says them in words; the comparison of results (reaction.species_from_output,
        modules/spectrum/analysis/quality.py) takes them from here.
          demo; error_termination; mpi_cpu_error; normal_exit_unconfirmed (no mark of a normal end, whatever else);
          scf_failed; optimization_unconverged (an optimization was run — more than one step — and did not converge);
          optimization_unconfirmed (one point: no convergence to confirm); raman_skipped; no_frequencies;
          imaginary_frequencies."""
        found = []
        if self.demo:
            found.append('demo')
        if self.error_module:
            found.append('error_termination')
        if self.mpi_cpu_error:
            found.append('mpi_cpu_error')
        if not self.normal_exit:
            found.append('normal_exit_unconfirmed')
        if self.scf_failed:
            found.append('scf_failed')
        if not self.optimization_converged:
            found.append('optimization_unconverged' if len(self.steps or ()) > 1 else 'optimization_unconfirmed')
        if self.raman_skipped:
            found.append('raman_skipped')
        if not self.frequencies:
            found.append('no_frequencies')
        elif self.imaginary:
            found.append('imaginary_frequencies')
        return tuple(found)

    @property
    def assessment(self):
        facts = set(self.facts)  # the words follow the codes of facts; the texts are those of before
        notes = [tr(n) for n in self.notes]
        if 'demo' in facts:
            notes.append(tr('Учебный синтетический пример. Эти числа не получены расчётным пакетом.'))
        if 'error_termination' in facts and self.program != 'ORCA':
            notes.append(
                tr(
                    f'{self.program}: аварийное завершение ({self.error_module}). Последние координаты и энергия могут относиться к незавершённому расчёту.'
                )
            )
        elif 'error_termination' in facts:
            notes.append(
                tr('ORCA сообщает об аварийном завершении на этапе ')
                + self.error_module
                + tr('. Последние координаты и энергия могут относиться к незавершённой оптимизации.')
            )
        if 'mpi_cpu_error' in facts:
            notes.append(
                tr(
                    'В журнале MPI найдено «Failed to get … cpu set». Проверьте конфигурацию запуска и распределение процессов; по этому сообщению нельзя судить о качестве геометрии.'
                )
            )
        if 'normal_exit_unconfirmed' in facts and 'error_termination' not in facts:
            notes.append(tr('Метка нормального завершения не найдена. Файл может быть неполным или расчёт прервался.'))
        if 'scf_failed' in facts:
            notes.append(tr('Найдено сообщение о несходимости SCF. Проверьте полный журнал.'))
        if facts & {'optimization_unconverged', 'optimization_unconfirmed'}:
            notes.append(
                tr('Подтверждение сходимости оптимизации не найдено. Для расчёта одной энергии это нормально.')
            )
        if 'raman_skipped' in facts:
            notes.append(tr('Раман не посчитан: ORCA считает активности Рамана только с численными частотами (NumFreq) — '
                            'в Секстанте галочка «Раман» ставит их сама.'))
        if 'no_frequencies' in facts:
            notes.append(tr('Частоты не найдены: характер стационарной точки по этому файлу не установлен.'))
        elif 'imaginary_frequencies' in facts:
            notes.append(
                tr(
                    f'Отрицательных частот: {len(self.imaginary)}. Проверьте моды и численную точность; минимум автоматически не подтверждён.'
                )
            )
        else:
            notes.append(
                tr(
                    'В прочитанных частотах нет отрицательных значений. Это не доказывает полноту расчёта или глобальность минимума.'
                )
            )
        if self.frequencies and self.geometry:
            n = len(self.geometry.atoms)
            # ORCA lists 3N frequencies (zeros for translations and rotations), the others 3N-6 (3N-5 linear)
            expected = (3 * n,) if self.program == 'ORCA' else (3 * n - 6, 3 * n - 5)
            if len(self.frequencies) not in expected:
                notes.append(tr('Число прочитанных частот отличается от 3N. Проверьте, не обрезан ли блок частот.'))
        return '\n\n'.join(notes)
