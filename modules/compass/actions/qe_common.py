"""What the parts of the crystal window share: the units, the headers of the steps, the notes of the programs, the
names of the tasks and the lines of the phonons.

Split off modules/compass/actions/qe_window.py (0.222.29).
"""

from azimuth.i18n import tr


RY_EV = 13.605693122994  # eV per Ry (CODATA 2018)
HEADER = '# ---- {} ({}) ----'  # a step in the shown file
NOTES = {  # under the settings, by the program
    'qe': 'Периодический расчёт ячейки кристалла плоскими волнами (pw.x, псевдопотенциалы SSSP efficiency для PBE или '
          'PBEsol, обрезки — из их таблицы). Считается одна ячейка файла, не блок на экране.',
    'cp2k': 'CP2K: гауссовы базисы MOLOPT и плоские волны для плотности (GPW) с псевдопотенциалами GTH или GFN1-xTB, '
            'расчёт в Γ-точке — для ячеек от ~10 Å (молекулярные кристаллы); маленькую ячейку считайте в суперячейке.'}


def task_title(title, kind='qe'):
    """«Оптимизация с ячейкой (vc-relax)» — the name of a task and the word of the program for it (what the
    papers and the manuals call it: calculation of pw.x, RUN_TYPE of CP2K)."""
    from modules.sextant import cp2k_inputs, qe_inputs

    words = ({k: v for k, v in cp2k_inputs.TASKS.items()} if kind == 'cp2k' else
             {**qe_inputs.TASKS, qe_inputs.BANDS_TASK: 'bands', qe_inputs.DOS_TASK: 'dos', qe_inputs.EOS_TASK: 'E(V)', qe_inputs.ELASTIC_TASK: 'E(ε)', qe_inputs.CUTOFF_TASK: 'ecutwfc', qe_inputs.KGRID_TASK: 'K_POINTS', qe_inputs.VACUUM_TASK: 'CELL_PARAMETERS', qe_inputs.HUBBARD_TASK: 'HUBBARD', qe_inputs.MAGNETIC_TASK: 'nspin',
              qe_inputs.PHONON_TASK: 'ph.x', qe_inputs.DISPERSION_TASK: 'ph.x, matdyn.x'})
    word = words.get(title)
    return f'{tr(title)} ({word})' if word else tr(title)


IMAGINARY_CM = -10.0  # cm⁻¹: a mode below is imaginary — the acoustic ones are 0 after the sum rule of dynmat.x


def phonon_lines(found):
    """The lines of the summary of «Частоты (точка Γ)» of pw.x, ph.x and dynmat.x: the optical modes, the imaginary
    ones (a structure not in its minimum), the IR-active ones, ε∞ (the mean of the diagonal)."""
    optical = [m.frequency for m in found.modes if abs(m.frequency) > -IMAGINARY_CM]
    imaginary = [f for f in optical if f < 0]
    lines = []
    real = [f for f in optical if f > 0]
    if real:
        lines.append(tr('Частоты в точке Γ: {} оптических мод, от {} до {} см⁻¹').format(
            len(real), f'{min(real):.1f}', f'{max(real):.1f}'))
    if imaginary:
        lines.append(tr('Мнимых мод: {} (до {} см⁻¹) — структура не в минимуме, сначала оптимизируйте её').format(
            len(imaginary), f'{min(imaginary):.1f}'))
    active = [m for m in found.modes if (m.intensity or 0) > 1.0]
    if active:
        lines.append(tr('ИК-активных мод: {}; самая сильная — {} см⁻¹, {} км/моль').format(
            len(active), f'{max(active, key=lambda m: m.intensity).frequency:.1f}',
            f'{max(m.intensity for m in active):.1f}'))
    if found.epsilon is not None:
        lines.append(tr('ε∞ (высокочастотная диэлектрическая проницаемость): {}').format(
            f'{sum(found.epsilon[k][k] for k in range(3)) / 3:.3f}'))
    lines.append(tr('Моды на модели: «Компас · Кристалл → Расчёт → Частоты (точка Γ)».'))
    return lines
