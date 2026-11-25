"""What the plots of Spectrum share: the reference result of a spectrum (its path, reading it), the error shown with
Quill, the export of a plot widget to a picture.

Split off modules/spectrum/views/spectra_view.py (0.222.30).
"""

from pathlib import Path
from PySide6.QtCore import QPointF, QSize
from PySide6.QtGui import QPainter
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtWidgets import QFileDialog
from azimuth.i18n import tr


def reference_path(parent, title):
    path, _ = QFileDialog.getOpenFileName(
        parent, title, str(Path.home()), tr('ORCA, Gaussian, xtb, Psi4, NWChem, Q-Chem, GAMESS, MOPAC (*.out *.log *.nwout *.qcout *.gamout);;Все файлы (*)')
    )
    return path


def show_error(parent, text):
    from azimuth import quill

    quill.warning(parent, tr('Не удалось выполнить действие'), text)  # Quill with the tangled ball


def read_reference(parent, path):
    """The result in another file for a comparison, or None with a message."""
    from modules.spectrum.readers.outputs import read_any

    try:
        text = Path(path).read_text(encoding='utf-8', errors='replace')
        return read_any(text, path)
    except (OSError, ValueError) as exc:
        show_error(parent, str(exc))
        return None


def _export_widget(widget, path, title, rows, header):
    suffix = path.suffix.lower()
    if suffix == '.csv':
        from modules.spectrum.wavefunction import field_tables

        field_tables.write_csv(path, header, rows)  # the style of «Таблицы CSV» (was «,», «.», no BOM)
    elif suffix == '.png':
        if not widget.grab().save(str(path)):
            raise OSError(tr('Не удалось сохранить PNG.'))
    elif suffix == '.svg':
        widget.grab()
        device = QSvgGenerator()
        device.setFileName(str(path))
        device.setSize(QSize(widget.width(), widget.height()))
        device.setViewBox(widget.rect())
        device.setTitle(title)
        painter = QPainter(device)
        if not painter.isActive():
            raise OSError(tr('Не удалось создать SVG.'))
        widget.render(painter, QPointF(0, 0).toPoint())
        painter.end()
    else:
        raise ValueError(tr('Поддерживаются PNG, SVG и CSV.'))
