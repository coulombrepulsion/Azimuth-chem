"""The spectrum of a mixture of conformers, averaged by their Boltzmann shares.

§1 PURPOSE
    A flexible molecule is a mixture of
    conformers, and what a spectrometer sees is the sum of their spectra, each with its share — without it the absolute
    configuration from ECD cannot be assigned, and IR and UV-Vis of a flexible molecule come out wrong. Spectrum
    already gave the shares («Инструменты → Энергии из нескольких файлов»); here the spectra are added by them.
§1 THEORY
    p_k from boltzmann.files_table (by G when every conformer has frequencies, else by E; its warnings — composition,
    level of theory, imaginary frequencies — said as they are). A broadened spectrum is linear in the intensities, so
    the averaged one is the spectrum of all the lines of all the conformers, each line × p_k: the IR intensities
    (Raman activities), the oscillator strengths, the rotatory strengths.
§4 SPECIFICATION
    conformers(paths, temperature, out_factor=1.0) -> {'paths', 'names', 'shares', 'by', 'warnings', 'rows',
      'outputs'} (the outputs of read_any, read once); ValueError of files_table.
    weighted_modes(mode_lists, shares) -> tuple of modes (intensity × share; a mode without one — left out);
    weighted_excitations(lists, shares) -> tuple of excitations (fosc, r_length, r_velocity × share).
    missing(names, lists) -> names of the conformers without the data (an empty tuple of modes, of excitations).
    weighted_shieldings(lists, shares) -> tuple of Shielding (σ of every atom — the sum of σ × share); ValueError
      when the conformers list other atoms or another order.
§7 TESTS
    tests/spectrum/test_ensemble.py.
"""

from dataclasses import replace
from pathlib import Path

from azimuth.i18n import tr


def conformers(paths, temperature, out_factor=1.0):
    from modules.spectrum.analysis import boltzmann, reaction
    from modules.spectrum.readers.outputs import read_any

    outputs = {}

    def read(path, label=None):
        p = Path(path)
        try:
            from modules.spectrum.readers.results import MAX_BYTES, too_large

            if p.stat().st_size > MAX_BYTES:
                raise too_large()
            text = p.read_text(encoding='utf-8', errors='replace')
        except OSError as exc:
            raise ValueError(tr('Не удалось прочитать файл: ') + f'{p.name} ({exc})') from exc
        output = read_any(text, str(p))
        outputs[str(p)] = output
        return reaction.species_from_output(output, text, str(p), label)

    paths = [str(p) for p in paths]
    if len(paths) < 2:
        raise ValueError(tr('Для среднего нужны хотя бы два конформера.'))
    found = boltzmann.files_table(paths, temperature, out_factor, read=read)
    return {'paths': paths, 'names': [row[0] for row in found['rows']], 'shares': [row[-1] for row in found['rows']],
            'by': found['by'], 'warnings': list(found['warnings']), 'rows': found['rows'],
            'outputs': [outputs[p] for p in paths]}


def missing(names, lists):
    return tuple(name for name, items in zip(names, lists) if not items)


def weighted_modes(mode_lists, shares):
    return tuple(replace(m, intensity=m.intensity * share)
                 for modes, share in zip(mode_lists, shares) for m in modes if m.intensity is not None)


def weighted_excitations(lists, shares):
    def times(value, share):
        return None if value is None else value * share

    return tuple(replace(e, fosc=e.fosc * share, r_length=times(e.r_length, share),
                         r_velocity=times(e.r_velocity, share))
                 for excitations, share in zip(lists, shares) for e in excitations)


def weighted_shieldings(lists, shares):
    """The shieldings of the mixture: of every atom the sum of σ × share over the conformers (they exchange faster
    than the spectrometer measures, and a nucleus gives one averaged signal). The conformers must list the same
    atoms in the same order; the anisotropy is not averaged (it is a property of one orientation) — None."""
    lists = [tuple(items) for items in lists]
    if not lists or len(lists) != len(shares):
        raise ValueError(tr('Для среднего нужны хотя бы два конформера.'))
    first = [(s.atom, s.element) for s in lists[0]]
    for items in lists[1:]:
        if [(s.atom, s.element) for s in items] != first:
            raise ValueError(tr('Конформеры различаются набором или порядком атомов — усреднять экранирования нельзя: '
                                'считайте ЯМР от геометрий с одной нумерацией.'))
    return tuple(replace(s, isotropic=sum(p * items[k].isotropic for p, items in zip(shares, lists)), anisotropy=None)
                 for k, s in enumerate(lists[0]))
