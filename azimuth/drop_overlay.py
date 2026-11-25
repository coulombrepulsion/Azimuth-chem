"""The veil over the window while files are dragged onto it.

While a file from Finder (or Explorer) is held over the window, the window turns grey and shows in its middle an icon
and what can be dropped in the section on screen — Compass: structures, Sextant: input files and structures, Spectrum:
results of calculations — with the extensions Azimuth reads (opening_actions.file_kind). The veil lets the mouse
through: the drag events still reach the window, which hides it on leaving or dropping.

DropOverlay(parent).show_for(section) — section 0 Compass, 1 Sextant, 2 Spectrum, other — everything; .hide().
TEXTS — {section: (title, extensions)}.
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from azimuth.i18n import tr

STRUCTURES = 'XYZ, MOL, SDF, MOL2, PDB, CIF, Molden, QCC'
INPUTS = 'ORCA .inp, Gaussian .gjf / .com, ' + STRUCTURES
RESULTS = ('ORCA, xtb, Psi4, MOPAC .out, Gaussian .log, NWChem .nwout, Q-Chem .qcout, GAMESS .gamout, Molden, '
           'FCHK, XYZ')
TEXTS = {
    0: ('Перенесите сюда файлы структуры', STRUCTURES),
    1: ('Перенесите сюда входные файлы или структуры', INPUTS),
    2: ('Перенесите сюда расчётные файлы', RESULTS),
    None: ('Перенесите сюда файлы', STRUCTURES + '; ORCA .inp, .out, Gaussian .gjf, .log'),
}


class DropOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.title = ''
        self.extensions = ''
        self.hide()

    def show_for(self, section):
        title, extensions = TEXTS.get(section, TEXTS[None])
        self.title, self.extensions = tr(title), tr(extensions)
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()
        self.update()

    def paintEvent(self, event):
        from azimuth.icons import icon

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = self.palette().window().color().lightness() < 128
        p.fillRect(self.rect(), QColor(20, 22, 26, 170) if dark else QColor(90, 94, 102, 150))
        margin = 28
        frame = QRectF(self.rect()).adjusted(margin, margin, -margin, -margin)
        pen = QPen(QColor(255, 255, 255, 210), 2.2, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(frame, 18, 18)
        size = 84
        centre = frame.center()
        p.drawPixmap(int(centre.x() - size / 2), int(centre.y() - size - 18),
                     icon('drop-files', '#ffffff').pixmap(size, size))
        font = p.font()
        font.setPointSizeF(font.pointSizeF() * 1.6)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(255, 255, 255))
        wide = QRectF(frame.left() + 20, centre.y(), frame.width() - 40, 44)
        p.drawText(wide, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, self.title)
        font.setPointSizeF(font.pointSizeF() / 1.6)
        font.setBold(False)
        p.setFont(font)
        p.setPen(QColor(255, 255, 255, 220))
        p.drawText(QRectF(frame.left() + 40, centre.y() + 48, frame.width() - 80, 60),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                   self.extensions)
