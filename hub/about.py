"""«О программе», the manual and the change log dialogs of the hub (moved from window.py)."""

import re

from PySide6.QtCore import (
    QSize,
    Qt,
    QUrl,
)
from PySide6.QtGui import (
    QDesktopServices,
    QFont,
    QIcon,
    QTextBlockFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
)

from azimuth.paths import ROOT
import azimuth
from hub.texts import TEXT
from hub.branding import sidebar_family, svg_pixmap, wordmark_pixmap, zh_wordmark_pixmap


DOC_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" '
    'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h9l4 4v14H6z"/>'
    '<path d="M15 3v4h4M9 11h7M9 15h7M9 19h4"/></g></svg>'
)
EMAIL = 'contact@azimuth-chem.com'  # the address of the site
# The motto: the home page shows it under the name, About under the wordmark. 0.248.0 (the owner: «Девиз думаю надо
# сменить у программы — этот девиз сейчас скорее к Атласу относится»; chosen: «Проложите курс к результату»); until
# then «Твой путеводитель по квантовой химии», which stays the Atlas's
MOTTO = {
    'ru': 'Проложите курс к результату',
    'en': 'Chart your course to the result',
    'zh': '规划通往结果的航线',
}
# the manual and the in-app journal (written for the reader, in Quail's voice); the technical
# changelog stays in CHANGELOG.md in the program folder
MANUAL = ROOT / 'docs' / 'manual'
JOURNAL = ROOT / 'docs' / 'journal'
AUTHOR_NOTE = re.compile(r'^\s*Правки внесла Jane\b.*$', re.MULTILINE)


def section_versions():
    """(module name, version) of Compass, Sextant and Spectrum (modules/<name>/__init__.py)."""
    import modules.compass
    import modules.sextant
    import modules.spectrum

    return [
        ('compass', getattr(modules.compass, '__version__', '')),
        ('sextant', getattr(modules.sextant, '__version__', '')),
        ('spectrum', getattr(modules.spectrum, '__version__', '')),
    ]


def justify(browser):
    """Every paragraph of a text browser justified (lists and headings too)."""
    cursor = QTextCursor(browser.document())
    cursor.select(QTextCursor.SelectionType.Document)
    block = QTextBlockFormat()
    block.setAlignment(Qt.AlignmentFlag.AlignJustify)
    cursor.mergeBlockFormat(block)
    browser.moveCursor(QTextCursor.MoveOperation.Start)


def journal_title(markdown):
    """(the "# " title of Quill's journal, the markdown without it)."""
    lines = markdown.splitlines()
    for k, line in enumerate(lines):
        if line.startswith('# '):
            return line[2:].strip(), '\n'.join(lines[:k] + lines[k + 1:]).strip() + '\n'
    return '', markdown


def read_localized(folder, language):
    """folder/<language>.md, the Russian one if that is missing, '' if neither exists."""
    for name in (language, 'ru'):
        path = folder / f'{name}.md'
        if path.is_file():
            return path.read_text(encoding='utf-8')
    return ''


def without_author_notes(markdown):
    """The technical changelog without the editor's attribution lines (they belong in CHANGELOG.md only)."""
    return re.sub(r'\n{3,}', '\n\n', AUTHOR_NOTE.sub('', markdown))


# the journal is sorted by section — general entries right under "## version", the others under
# "### Атлас / Компас / Секстант / Спектр" (or their English and Chinese names); the changelog window shows
# one tab per section
SECTION_KEYS = ('program', 'atlas', 'compass', 'sextant', 'spectrum')
JOURNAL_HEADINGS = {
    'atlas': ('Атлас', 'Atlas', '图谱'),
    'compass': ('Компас', 'Compass', '罗盘'),
    'sextant': ('Секстант', 'Sextant', '六分仪'),
    'spectrum': ('Спектр', 'Spectrum', '光谱'),
}


def journal_page(markdown):
    """The journal as shown in «Что нового».

    An entry is «- ### title» and its text under it — Qt's Markdown took the text for the list item and every next entry
    for a list inside the one before; shown, the title is a heading of its own.

    The versions 0.206.0, 0.206.1 … stand under one heading «0.206 — 15–17 ноября 2026», each under a
    subheading of its own."""
    import re

    markdown = re.sub(r'^- (#{3,4} )', r'\1', markdown, flags=re.MULTILINE)
    version = re.compile(r'^## (\d+\.\d+)\.(\d+)\s*[—–-]\s*(.+?)\s*$')
    out, group = [], None  # group: [minor, [dates], [lines]]

    def flush():
        if group is None:
            return
        out.append(f'## {group[0]} — {journal_span(group[1])}')
        out.append('')
        out.extend(group[2])

    for line in markdown.splitlines():
        found = version.match(line)
        if found:
            minor, patch, date = found.group(1), found.group(2), found.group(3)
            if group is None or group[0] != minor:
                flush()
                group = [minor, [], []]
            group[1].append(date)
            group[2].append(f'@@ {minor}.{patch}')  # its subheading — unless its first entry is one already
            continue
        if line.startswith('## ') or line.startswith('# '):
            flush()
            group = None
            out.append(line)
            continue
        (group[2] if group is not None else out).append(line)
    flush()
    shown, waiting = [], None
    for line in out:  # a version whose text begins with its own «### 0.206.3 — …» keeps it; others get «### 0.206.3»
        if line.startswith('@@ '):
            waiting = line[3:]
            continue
        if waiting is not None and line.strip():
            if not line.startswith('### ' + waiting):
                shown.extend([f'### {waiting}', ''])
            waiting = None
        shown.append(line)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(shown))


def frame_parts(markdown):
    """[(framed, text)] of journal_page(): a version of a minor («### 0.248.3 …» and its text, up to the next «###» or
    «##») is framed; the headings of the minors and the rest are not (0.248.11)."""
    parts, block, framed = [], [], False

    def flush():
        text = '\n'.join(block).strip('\n')
        if text.strip():
            parts.append((framed, text))

    for line in markdown.splitlines():
        if line.startswith('### ') or line.startswith('## ') or line.startswith('# '):
            flush()
            block, framed = [line], line.startswith('### ')
            continue
        block.append(line)
    flush()
    return parts


def fill_journal(page, markdown, line='#d8dce3'):
    """The journal into the browser: the headings of the minors as they are, each version in a frame with a thin line
    round it (the owner, 2026-11-27: «в что нового каждая версия, например 0.248, а под ней подверсии в рамке
    отделены»)."""
    from PySide6.QtGui import QColor, QTextCursor, QTextFrameFormat

    page.clear()
    document = page.document()
    frames, after_heading = [], False
    for framed, text in frame_parts(markdown):
        cursor = QTextCursor(document)
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if not framed:
            cursor.insertMarkdown(text + '\n')
            after_heading = text.startswith('## ')  # room under the heading of a version (0.248.13)
            continue
        shape = QTextFrameFormat()
        shape.setBorder(0)  # the line round it is drawn by JournalBrowser, with round corners
        shape.setPadding(9)
        shape.setLeftMargin(6)
        shape.setRightMargin(6)
        shape.setTopMargin(10 if after_heading else 0)
        after_heading = False
        shape.setBottomMargin(0)  # the empty line Qt keeps after a frame is the gap between two
        frame = cursor.insertFrame(shape)
        inner = frame.firstCursorPosition()
        inner.insertMarkdown(text)
        frames.append(frame)
    page.journal_frames, page.frame_line = frames, QColor(line)
    page.viewport().update()


def journal_browser():
    """A QTextBrowser that draws a line with round corners round each frame of fill_journal (a frame of Qt's text has
    square corners only; the owner: «рамки скругленные, как и почти все в программе»)."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QPainter, QPen

    class JournalBrowser(QTextBrowser):
        journal_frames = ()
        frame_line = None
        RADIUS = 9

        def paintEvent(self, event):
            super().paintEvent(event)
            if not self.journal_frames or self.frame_line is None:
                return
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.translate(-self.horizontalScrollBar().value(), -self.verticalScrollBar().value())
            painter.setPen(QPen(self.frame_line, 1))
            layout = self.document().documentLayout()
            for frame in self.journal_frames:
                try:
                    box = QRectF(layout.frameBoundingRect(frame))
                    shape = frame.frameFormat()
                    box = box.adjusted(shape.leftMargin() + 0.5, shape.topMargin() + 0.5,
                                       -shape.rightMargin() - 0.5, -shape.bottomMargin() - 0.5)
                except RuntimeError:  # the document was filled again
                    continue
                painter.drawRoundedRect(box, self.RADIUS, self.RADIUS)
            painter.end()

    return JournalBrowser()


MONTHS = {
    'ru': ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября',
           'декабря'),
    'en': ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November',
           'December'),
}


def _journal_date(text):
    """(year, month, day, the language) of a date of the journal («17 ноября 2026», «17 November 2026»,
    «2026 年 11 月 17 日»), or None."""
    import re

    found = re.match(r'^(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日$', text)
    if found:
        return int(found.group(1)), int(found.group(2)), int(found.group(3)), 'zh'
    found = re.match(r'^(\d{1,2})\s+(\S+)\s+(\d{4})$', text)
    if found:
        for language, names in MONTHS.items():
            if found.group(2) in names:
                return int(found.group(3)), names.index(found.group(2)) + 1, int(found.group(1)), language
    return None


def journal_span(dates):
    """The dates of the versions of one heading as one date or a span: «17 ноября 2026», «15–17 ноября 2026»,
    «30 октября – 2 ноября 2026»; a date not understood is shown as it is (the newest)."""
    parsed = [_journal_date(d) for d in dates]
    if not dates:
        return ''
    if any(p is None for p in parsed):
        return dates[0]
    first, last = min(parsed), max(parsed)
    if first[:3] == last[:3]:
        return dates[parsed.index(last)]
    language = last[3]
    if language == 'zh':
        if first[:2] == last[:2]:
            return f'{last[0]} 年 {last[1]} 月 {first[2]}–{last[2]} 日'
        return f'{first[0]} 年 {first[1]} 月 {first[2]} 日 – {last[0]} 年 {last[1]} 月 {last[2]} 日'
    names = MONTHS[language]
    if first[:2] == last[:2]:
        return f'{first[2]}–{last[2]} {names[last[1] - 1]} {last[0]}'
    if first[0] == last[0]:
        return f'{first[2]} {names[first[1] - 1]} – {last[2]} {names[last[1] - 1]} {last[0]}'
    return f'{first[2]} {names[first[1] - 1]} {first[0]} – {last[2]} {names[last[1] - 1]} {last[0]}'


def split_journal(markdown):
    """{section key: markdown} of Quail's journal: 'program' keeps the title, the notes on top and the general
    entries of every version; each section gets the "## version" headings with its own entries only."""
    owner = {name: key for key, names in JOURNAL_HEADINGS.items() for name in names}
    lines = {key: [] for key in SECTION_KEYS}
    pending = {key: [] for key in SECTION_KEYS}  # the "## version" heading, written with the first entry
    current = 'program'
    for line in markdown.splitlines():
        if line.startswith('## '):
            current = 'program'
            for key in SECTION_KEYS:
                pending[key] = [line, '']
            continue
        if line.startswith('### ') and line[4:].strip() in owner:
            current = owner[line[4:].strip()]
            continue
        if line.startswith('# ') or (not pending['program'] and not lines['program'] and current == 'program'):
            lines['program'].append(line)
            continue
        if not line.strip():
            if lines[current] and lines[current][-1].strip():
                lines[current].append('')
            continue
        if pending[current]:
            if lines[current] and lines[current][-1].strip():
                lines[current].append('')
            lines[current].extend(pending[current])
            pending[current] = []
        lines[current].append(line)
    return {key: '\n'.join(lines[key]).strip() + '\n' for key in SECTION_KEYS}


PROGRAM = {
    'ru': {
        'intro': '«Азимут» — учебная программа по квантовой химии: теория в Атласе на сайте azimuth-chem.com, '
        'молекула в Компасе, подготовка расчёта в Секстанте и разбор его результатов в Спектре — в одном окне.',
        'sections': [
            ('Атлас', '43 интерактивные темы теории на русском, английском и китайском — на сайте azimuth-chem.com: численные модели считаются прямо в браузере, у каждой темы есть демонстрация и задания с выбором ответа; программа открывает его в браузере, а молекулу из темы — в Компасе.'),
            ('Компас · Молекула', 'построение и редактирование молекул: фрагменты, библиотека из 106 молекул, SMILES, ChemDraw, пептиды и координационные центры, силовое поле UFF, симметрия, название по IUPAC, редактор Z-матрицы; проверка структуры, явный растворитель, протоны и изотопы; шаги оптимизации, сканы и путь IRC, заряды, порядки связей и силы, орбитали, плотность и карта ESP прямо на модели; проекты с наборами молекул и историей их расчётов, в том числе из готовых расчётов; рисунки PNG, SVG, PDF.'),
            ('Компас · Кристалл', 'кристаллы из CIF, выходов CRYSTAL и базы COD: ячейка и симметрия, блок ячеек и поверхность (hkl), контакты и водородные связи, π-стопки, поверхность Хиршфельда, энергии пар, порошковая дифрактограмма; расчёт в Quantum ESPRESSO и CP2K, входной файл CRYSTAL; заряды, связи AIM, зоны и плотность состояний; CIF, POSCAR и расширенный XYZ.'),
            ('Секстант', 'подготовка и запуск расчёта в ORCA, Gaussian, Psi4, xtb, MOPAC, GAMESS или NWChem, для кристаллов — в Quantum ESPRESSO и CP2K: метод, базис, задача (в том числе UV-Vis и ЯМР), растворитель и дисперсия; редактор входного файла с подсветкой, очереди и цепочки расчётов, доктор неудачного расчёта; на этом компьютере или на сервере со SLURM — несколько расчётов сразу, файлы на сервере и очередь кластера; результат открывается сам.'),
            ('Спектр', 'результаты ORCA, Gaussian, Psi4, xtb, MOPAC, NWChem, Q-Chem, GAMESS, Firefly, а у кристаллов — Quantum ESPRESSO, CP2K и CRYSTAL: энергии, колебания, ИК и ВКД, UV-Vis, ЭКД и излучение, ЯМР, термохимия, сходимость оптимизации; сравнение с экспериментом и NIST, среднее по конформерам; орбитали и плотность — из файлов Molden, fchk, вывода ORCA или CUBE.'),
        ],
        'note': 'Расчётные программы (ORCA и другие) устанавливаются отдельно и в «Азимут» не входят.',
        'author': 'Автор — С. А. Собалев. Замечания и предложения:',
        'sections_title': 'Разделы',
        'version': 'Версия',
        'changelog': 'Журнал изменений',
        'manual': 'Руководство',
        'program_tab': 'Программа',
        'atlas_tab': 'Атлас',
        'atlas_tech': 'Технические изменения Атласа',
        'latest': 'Последняя запись',
        'journal_sub': 'Что нового в программе и в каждом её разделе.',
    },
    'en': {
        'intro': 'Azimuth is a teaching program for quantum chemistry: theory in the Atlas on azimuth-chem.com, the '
        'molecule in Compass, preparing a calculation in Sextant and reading its results in Spectrum — in one window.',
        'sections': [
            ('Atlas', '43 interactive theory topics in Russian, English and Chinese — on azimuth-chem.com: the numerical models run right in the browser, every topic has a demo and multiple-choice tasks; the program opens it in the browser, and a molecule of a topic in Compass.'),
            ('Compass · Molecule', 'building and editing molecules: fragments, a library of 106 molecules, SMILES, ChemDraw, peptides and coordination centres, the UFF force field, symmetry, IUPAC names, a Z-matrix editor; a structure check, explicit solvent, protons and isotopes; optimization steps, scans and the IRC path, charges, bond orders and forces, orbitals, densities and an ESP map right on the model; projects with sets of molecules and the history of their calculations, also made from finished calculations; PNG, SVG, PDF pictures.'),
            ('Compass · Crystal', 'crystals from CIF, CRYSTAL outputs and the COD database: the cell and its symmetry, a block of cells and a (hkl) surface, contacts and hydrogen bonds, π-stacks, the Hirshfeld surface, pair energies, the powder pattern; calculations in Quantum ESPRESSO and CP2K, a CRYSTAL input file; charges, AIM bonds, bands and the density of states; CIF, POSCAR and extended XYZ.'),
            ('Sextant', 'preparing and running a calculation in ORCA, Gaussian, Psi4, xtb, MOPAC, GAMESS or NWChem, for crystals in Quantum ESPRESSO and CP2K: method, basis, task (UV-Vis and NMR too), solvent and dispersion; an input editor with highlighting, queues and chains of calculations, a doctor for a failed calculation; on this computer or on a SLURM server — several calculations at once, the files on the server and the cluster queue; the result opens by itself.'),
            ('Spectrum', 'results of ORCA, Gaussian, Psi4, xtb, MOPAC, NWChem, Q-Chem, GAMESS and Firefly, and for crystals of Quantum ESPRESSO, CP2K and CRYSTAL: energies, vibrations, IR and VCD, UV-Vis, ECD and emission, NMR, thermochemistry, optimization convergence; comparison with experiment and NIST, the conformer average; orbitals and densities — from Molden, fchk, ORCA output or CUBE files.'),
        ],
        'note': 'The calculation programs (ORCA and others) are installed separately and are not part of Azimuth.',
        'author': 'Author: S. A. Sobalev. Comments and suggestions:',
        'sections_title': 'Sections',
        'version': 'Version',
        'changelog': 'Changelog',
        'manual': 'Manual',
        'program_tab': 'Program',
        'atlas_tab': 'Atlas',
        'atlas_tech': 'Technical changes of the Atlas',
        'latest': 'Latest entry',
        'journal_sub': 'What is new in the program and in each of its sections.',
    },
    'zh': {
        'intro': '“方位”是一个量子化学教学程序：在 azimuth-chem.com 网站上的图谱中学习理论，在罗盘中构建分子，在六分仪中准备计算，'
        '在光谱中分析结果——都在同一个窗口中。',
        'sections': [
            ('图谱', '43 个交互式理论主题，俄语、英语和中文——在 azimuth-chem.com 网站上：数值模型直接在浏览器中计算，每个主题都有演示和选择题；程序在浏览器中打开它，并在罗盘中打开主题里的分子。'),
            ('罗盘 · 分子', '构建和编辑分子：片段、106 个分子的分子库、SMILES、ChemDraw、肽和配位中心、UFF 力场、对称性、IUPAC 命名、Z 矩阵编辑器；结构检查、显式溶剂、质子和同位素；优化步骤、扫描和 IRC 路径，电荷、键级和受力，以及直接显示在模型上的轨道、密度和 ESP 图；包含分子集及其计算历史的项目，也可由已完成的计算创建；PNG、SVG、PDF 图片。'),
            ('罗盘 · 晶体', '来自 CIF、CRYSTAL 输出和 COD 数据库的晶体：晶胞与对称性、晶胞块和（hkl）表面、接触和氢键、π 堆积、Hirshfeld 表面、分子对能量、粉末衍射图；Quantum ESPRESSO 和 CP2K 计算、CRYSTAL 输入文件；电荷、AIM 键、能带和态密度；CIF、POSCAR 和扩展 XYZ。'),
            ('六分仪', '在 ORCA、Gaussian、Psi4、xtb、MOPAC、GAMESS 或 NWChem 中准备并运行计算，晶体则用 Quantum ESPRESSO 和 CP2K：方法、基组、任务（包括 UV-Vis 和 NMR）、溶剂和色散；带语法高亮的输入文件编辑器、计算队列和计算链、失败计算的“诊断”；在本机或 SLURM 服务器上运行——可同时运行多个计算，管理服务器文件和集群队列；结果自动打开。'),
            ('光谱', 'ORCA、Gaussian、Psi4、xtb、MOPAC、NWChem、Q-Chem、GAMESS 和 Firefly 的结果，晶体则有 Quantum ESPRESSO、CP2K 和 CRYSTAL 的结果：能量、振动、红外和 VCD、UV-Vis、ECD 和发射、NMR、热化学、优化收敛；与实验和 NIST 比较、构象平均；轨道和密度——来自 Molden、fchk、ORCA 输出或 CUBE 文件。'),
        ],
        'note': '计算程序（ORCA 等）需另行安装，不包含在“方位”中。',
        'author': '作者：S. A. Sobalev。意见与建议：',
        'sections_title': '组成部分',
        'version': '版本',
        'changelog': '更新日志',
        'manual': '使用手册',
        'program_tab': '程序',
        'atlas_tab': '图谱',
        'atlas_tech': '图谱的技术更改',
        'latest': '最新记录',
        'journal_sub': '程序及其各个部分的新变化。'
    },
}


BOOK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" '
    'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5.5C5.5 4 8.5 4 12 6c3.5-2 '
    '6.5-2 9-.5V19c-2.5-1.5-5.5-1.5-9 .5-3.5-2-6.5-2-9-.5z"/><path d="M12 6v13.5"/></g></svg>'
)


def split_manual(markdown):
    """[(tab title, markdown)] of the manual: one tab per "## " section; the title and the
    introduction above the first section open the first tab."""
    head, sections, title, lines = [], [], None, []
    for line in markdown.splitlines():
        if line.startswith('## '):
            if title is not None:
                sections.append((title, '\n'.join(lines).strip() + '\n'))
            title, lines = line[3:].strip(), []
            continue
        (head if title is None else lines).append(line)
    if title is not None:
        sections.append((title, '\n'.join(lines).strip() + '\n'))
    if not sections:
        return [('', markdown)]
    first_title, first_body = sections[0]
    sections[0] = (first_title, '\n'.join(head).strip() + '\n\n' + first_body)
    return sections


def manual_pdf(language):
    """The book of the manual in the language (docs/manual/Azimuth-manual-<language>.pdf, made by tools/manual_pdf.py)
    or None when there is none yet."""
    path = MANUAL / f'Azimuth-manual-{language}.pdf'
    return path if path.is_file() else None


def open_manual(parent, language):
    """«Руководство»: the PDF in the reader of the system when the language has one (a book with its contents,
    pictures and bookmarks); else — and when the system opens nothing — the dialog with the Markdown, returned so that
    the caller keeps it alive."""
    path = manual_pdf(language)
    if path is not None and QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
        return None
    dialog = ManualDialog(parent, language)
    dialog.open()
    return dialog


class ManualDialog(QDialog):
    """The manual (docs/manual/<language>.md): what each section can do and how to do it, one tab per
    section of the program."""

    def __init__(self, parent, language):
        super().__init__(parent)
        self.setWindowTitle(PROGRAM[language]['manual'])
        self.resize(820, 780)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.pages = []
        for title, body in split_manual(read_localized(MANUAL, language)):
            # the pictures of the book are screenshots 1800 px wide: the dialog shows the text only
            body = re.sub(r'^!\[[^\]]*\]\([^)]*\)\s*$', '', body, flags=re.MULTILINE)
            page = QTextBrowser()
            page.setOpenExternalLinks(True)
            page.setMarkdown(body)
            self.pages.append(page)
            self.tabs.addTab(page, title)
        self.body = self.pages[0]
        layout.addWidget(self.tabs)
        close = QPushButton(TEXT[language]['close'])
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)


QUILL_NOTES = ROOT / 'assets' / 'quill' / 'quill-journal.webp'  # Quill with the pile of her notes (QUAIL_ART.md № 17)
QUILL_SIZE = 140  # px: the height of Quill in the head of «Что нового» (larger by the owner's wish)
# a brown quill pen writing: the vane, the shaft, the nib on the line and a stroke of ink after it
WRITING_QUILL_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
                     '<path d="M21 2.2c-5.2.4-9.8 4-11.9 9.6l-1.3 3.9 3.9-1.3c5.6-2.1 9.2-6.7 9.3-12.2z" '
                     'fill="#c08a52" stroke="#7a4a1f" stroke-width="0.8" stroke-linejoin="round"/>'
                     '<path d="M13.6 8.6l-2.2.4M15.8 6.6l-2.4.3M12.2 11.2l-1.6.6" stroke="#8a5a2b" '
                     'stroke-width="0.6" stroke-linecap="round"/>'
                     '<path d="M20.4 2.8L7 16.2" stroke="#5e3816" stroke-width="1" stroke-linecap="round"/>'
                     '<path d="M8.2 15L4.6 19.6" stroke="#3b2a1a" stroke-width="1.3" stroke-linecap="round"/>'
                     '<path d="M1.8 21.6c1-.9 1.8-.9 2.5-.1s1.5.8 2.3 0 1.6-.8 2.4 0 1.5.7 2.2.1" fill="none" '
                     'stroke="#8a5a2b" stroke-width="0.9" stroke-linecap="round"/></svg>')


def quill_notes_picture(ratio=1.0):
    """Quill of the head of the journal, mirrored (she looks to the left, at the text), QUILL_SIZE logical pixels high
    (a null QPixmap if the file is missing)."""
    from PySide6.QtGui import QPixmap

    from PySide6.QtGui import QTransform

    picture = QPixmap(str(QUILL_NOTES))
    if picture.isNull():
        return picture
    picture = picture.transformed(QTransform().scale(-1, 1))  # turned to the left, to the text (the owner)
    ratio = max(1.0, float(ratio))
    picture = picture.scaledToHeight(round(QUILL_SIZE * ratio), Qt.TransformationMode.SmoothTransformation)
    picture.setDevicePixelRatio(ratio)
    return picture


class ChangelogDialog(QDialog):
    """Quail's journal (docs/journal) with one tab per section: the program as a whole, the Atlas
    (with its technical changelog, without the editor's attribution lines), Compass, Sextant and Spectrum."""

    def __init__(self, parent, language):
        super().__init__(parent)
        words, text = PROGRAM[language], TEXT[language]
        self.setWindowTitle(words['changelog'])
        self.resize(760, 720)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        # the tabs begin where the round corner of the page ends, as the tabs elsewhere (0.248.14)
        self.tabs.setStyleSheet('QTabWidget::tab-bar {left: 10px;}')
        parts = split_journal(read_localized(JOURNAL, language))  # Quail's journal, not CHANGELOG.md
        # Quill with her notes and the title of the journal above the tabs (the title left the first tab)
        title, parts['program'] = journal_title(parts['program'])
        from azimuth import quill

        # a card — Quill with her journal, the title, a line about the journal, the latest entry and the versions of all
        # the sections (no blue strip — that is of the dialogs of Quill)
        versions = dict(section_versions())
        versions['program'] = azimuth.__version__
        versions['atlas'] = ''  # the Atlas (on the site) gave its version when it was in the window
        dark = self.palette().window().color().lightnessF() < 0.5
        accent = '#6ea2f0' if dark else '#2a62b8'
        card = QFrame()
        card.setObjectName('journalHead')
        # the head on the ground of the window; the light blue tint is the ground of the notes (the pages below)
        tint = "rgba(110, 162, 240, 0.10)" if dark else "rgba(42, 98, 184, 0.06)"
        card.setStyleSheet(
            # without the strip
            'QFrame#journalHead {background: transparent; border: none;}'
            'QFrame#journalHead QLabel {background: transparent;}'
        )
        head = QHBoxLayout(card)
        head.setContentsMargins(16, 12, 18, 12)
        head.setSpacing(16)
        self.picture = QLabel()
        # quill-journal (with the pile of papers, docs/art/QUAIL_ART.md № 17) once it is drawn; until then the notes
        picture = quill.pixmap('journal', 72)  # the open book of the journal (azimuth/state_icons.py)
        if not picture.isNull():
            self.picture.setPixmap(picture)
        head.addWidget(self.picture, 0, Qt.AlignmentFlag.AlignVCenter)
        column = QVBoxLayout()
        column.setSpacing(4)
        self.title = QLabel(title)
        self.title.setWordWrap(True)
        family = sidebar_family()
        self.title.setStyleSheet(f"font-size: 22px; font-weight: 600;{f' font-family: {chr(39)}{family}{chr(39)};' if family else ''}")
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.title.setWordWrap(False)  # one line, the pen right after it
        title_row.addWidget(self.title, 0, Qt.AlignmentFlag.AlignVCenter)
        # a brown quill that writes, by the title (0.248.14, the owner: «Добавь рядом с Заметки Квил перо коричневое,
        # которое типа пишет»)
        self.pen = QLabel()
        self.pen.setObjectName('journalPen')
        self.pen.setPixmap(svg_pixmap(WRITING_QUILL_SVG, '#8a5a2b', 34, max(1.0, self.devicePixelRatioF())))
        title_row.addWidget(self.pen, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch(1)
        column.addLayout(title_row)
        subtitle = QLabel(words.get('journal_sub', ''))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f'font-size: 13px; color: {"#9aa3b2" if dark else "#5b6474"};')
        column.addWidget(subtitle)
        latest = re.search(r'(?m)^## (\S+) — (.+)$', read_localized(JOURNAL, language))
        if latest:
            self.latest = QLabel(f"{words.get('latest', '')}: <b>{latest.group(1)}</b> · {latest.group(2).strip()}")
            self.latest.setStyleSheet('font-size: 13px;')
            column.addWidget(self.latest)
        chips = QHBoxLayout()
        chips.setSpacing(6)
        for key in SECTION_KEYS:
            if not versions.get(key):
                continue
            name = words['program_tab'] if key == 'program' else text[key]
            chip = QLabel(f'{name} <span style="color:{accent}; font-weight:600">{versions[key]}</span>')
            chip.setStyleSheet(f'font-size: 12px; padding: 2px 8px; border: 1px solid {accent}; border-radius: 9px;')
            chips.addWidget(chip)
        chips.addStretch(1)
        column.addSpacing(4)
        column.addLayout(chips)
        head.addLayout(column, 1)
        # Quill with the pile of her notes in the right corner (0.248.14, the owner: «можно справа в угол что нового
        # вернуть картинку Квил»): the journal is still written by her
        self.quill = QLabel()
        self.quill.setObjectName('journalQuill')
        notes = quill_notes_picture(self.devicePixelRatioF())
        if not notes.isNull():
            self.quill.setPixmap(notes)
        head.addWidget(self.quill, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(card)
        self.pages = {}
        for key in SECTION_KEYS:
            page = journal_browser()
            page.setOpenExternalLinks(True)
            body = parts[key]
            if key != 'program' and versions.get(key):
                body = f"*{words['version']} {versions[key]}*\n\n" + body
            fill_journal(page, journal_page(body), '#2b333f' if dark else '#d8dce3')
            if key == 'atlas':
                technical = ROOT / 'modules' / 'atlas' / 'atlas_v2' / 'CHANGELOG.md'
                if technical.is_file():
                    page.append(f"<h2>{words['atlas_tech']}</h2>")
                    cursor = page.textCursor()
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    cursor.insertMarkdown(without_author_notes(technical.read_text(encoding='utf-8')))
            justify(page)
            page.setStyleSheet(f'QTextBrowser {{background: {tint}; border: none; border-radius: 10px; padding: 6px 10px;}}')
            self.pages[key] = page
            self.tabs.addTab(page, words['program_tab'] if key == 'program' else text[key])
        self.program = self.pages['program']
        layout.addWidget(self.tabs)
        close = QPushButton(TEXT[language]['close'])
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)


class AboutDialog(QDialog):
    """About Azimuth: what the program is, versions, author and contact, citation, link to the changelog."""

    def __init__(self, parent, language, dark=False):
        super().__init__(parent)
        text, words = TEXT[language], PROGRAM[language]
        self.language = language
        self.setWindowTitle(text['about'])
        self.resize(600, 620)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        head = QHBoxLayout()
        head.setSpacing(14)
        icon = QLabel()
        # the tile of the theme of the program (0.248.13 — the owner: «иконка в О программе будет соответствующей темы,
        # как и сама программа»; the icon of the window follows the appearance of the system)
        from azimuth.app import app_icon

        icon.setPixmap(app_icon(dark).pixmap(QSize(64, 64)))
        head.addWidget(icon)
        names = QVBoxLayout()
        names.setSpacing(2)  # the motto close under the name (0.248.13)
        mark = QLabel()
        if language == 'zh':
            mark.setPixmap(
                zh_wordmark_pixmap(
                    22,
                    self.devicePixelRatioF(),
                    '#e7eaf0' if dark else '#1b2230',
                    '#6ea2f0' if dark else '#2a62b8',
                    sidebar_family(),
                )
            )
            mark.setAccessibleName(text['brand'])
        else:
            mark.setPixmap(wordmark_pixmap(language, 22, self.devicePixelRatioF(), dark))
        names.addWidget(mark)
        self.motto = QLabel(MOTTO[language])  # the motto of the home page instead of the subtitle
        # in the face of the home page (Golos Text SemiBold, capitals, tracked like the name)
        from hub.home import motto_family

        if language != 'zh':
            self.motto.setText(MOTTO[language].upper())
        strict = motto_family() or sidebar_family()
        face = f"font-family: '{strict}'; " if strict else ''
        self.motto.setStyleSheet(f"color: {'#9aa3b2' if dark else '#5b6474'}; {face}font-size: 11px; font-weight: 600;")  # 13 until 0.248.13
        mfont = QFont(self.motto.font())
        mfont.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 114)
        self.motto.setFont(mfont)
        names.addWidget(self.motto)
        # the versions of the program and of every section in the header, once (the table is gone)
        self.versions = QLabel(self.version_line())
        self.versions.setObjectName('subtitle')
        self.versions.setWordWrap(True)
        names.addWidget(self.versions)
        head.addLayout(names, 1)
        layout.addLayout(head)
        self.body = QTextBrowser()
        self.body.setOpenExternalLinks(True)
        self.body.setHtml(self.html())
        justify(self.body)
        self.body.setViewportMargins(0, 0, 14, 0)  # the text off the scroll bar (0.248.11)
        layout.addWidget(self.body, 1)
        self.changelog_link = QPushButton(words['changelog'])
        self.changelog_link.setFlat(True)
        self.changelog_link.setCursor(Qt.CursorShape.PointingHandCursor)
        accent = '#6ea2f0' if dark else '#2a62b8'
        self.changelog_link.setIcon(QIcon(svg_pixmap(DOC_SVG, accent, 18, self.devicePixelRatioF())))
        self.changelog_link.setIconSize(QSize(18, 18))
        self.changelog_link.setStyleSheet(
            f'QPushButton {{border: none; background: transparent; color: {accent}; '
            f'text-align: left; padding: 2px 0; font-weight: 600;}} '
            f'QPushButton:hover {{text-decoration: underline;}}'
        )
        self.changelog_link.clicked.connect(self.show_changelog)
        self.manual_link = QPushButton(words['manual'])
        self.manual_link.setFlat(True)
        self.manual_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manual_link.setIcon(QIcon(svg_pixmap(BOOK_SVG, accent, 18, self.devicePixelRatioF())))
        self.manual_link.setIconSize(QSize(18, 18))
        self.manual_link.setStyleSheet(self.changelog_link.styleSheet())
        self.manual_link.clicked.connect(self.show_manual)
        links = QHBoxLayout()
        links.setSpacing(22)
        links.addWidget(self.manual_link)
        links.addWidget(self.changelog_link)
        links.addStretch(1)
        layout.addLayout(links)
        buttons = QHBoxLayout()
        # no «Скопировать ссылку» — the citation of the Atlas came from the Atlas in the window
        self.bug_button = QPushButton(text['bug'])
        self.bug_button.clicked.connect(self._report)
        buttons.addWidget(self.bug_button)
        buttons.addStretch(1)
        close = QPushButton(text['close'])  # what closes is white (the rule of the buttons, azimuth/app.py)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def version_line(self):
        """Программа 0.55.0 · Атлас 2.14.0 · Компас 1.7.0 · Секстант 1.6.0 · Спектр 1.1.0"""
        text = TEXT[self.language]
        parts = [f"{text['program']} {azimuth.__version__}"]
        parts += [f'{text[ident]} {version}' for ident, version in section_versions() if version]
        return ' · '.join(parts)

    def html(self):
        words = PROGRAM[self.language]
        site = '<a href="https://www.azimuth-chem.com/">azimuth-chem.com</a>'  # a link (0.248.11)
        items = ''.join(f'<li><b>{name}</b> — {desc}</li>' for name, desc in words['sections']).replace(
            'azimuth-chem.com', site)
        return (
            f"<p>{words['intro'].replace('azimuth-chem.com', site)}</p><h4>{words['sections_title']}</h4><ul>{items}</ul>"
            f"<p>* {words['note']}</p><p>{words['author']} <a href=\"mailto:{EMAIL}\">{EMAIL}</a></p>"
        )

    def show_manual(self):
        self.manual = open_manual(self, self.language)

    def show_changelog(self):
        self.changelog = ChangelogDialog(self, self.language)
        self.changelog.open()

    def _report(self):
        QDesktopServices.openUrl(QUrl(f'mailto:{EMAIL}'))
