"""The user manual as one PDF: docs/manual/<lang>.md → docs/manual/Azimuth-manual-<lang>.pdf.

§1 PURPOSE
    The manual is written once, in Markdown (docs/manual/ru.md); the program shows it, and this tool makes of it a book
    to print or read on a screen: a title page, a table of contents with page numbers, numbered chapters, sections and
    subsections, numbered figures and tables, a running header and page numbers, and bookmarks of the PDF reader.
§2 ALGORITHM
    1. The Markdown of the manual is turned into HTML (to_html): «## » — a chapter (1, 2 …; «## Приложение А. …» —
       an appendix А, Б …), «### » — a section (1.1), «#### » — a subsection (1.1.1); a paragraph that is only an
       image — a figure «Рисунок N.k» with the text of the image as its caption; a line «Таблица: …» right above a
       table — the caption «Таблица N.k»; «> **Примечание.** …» — a framed note. Every heading gets an id; the table
       of contents links to them.
    2. The page is printed to PDF by the Chromium of Qt (QWebEnginePage.printToPdf) twice: the first PDF says on which
       page every heading stands (its named destinations, /Dests), the second has these numbers in the table of
       contents. The numbers take the same room in both, so the pages do not move; the build checks it.
    3. The bookmarks (the outline of the PDF: chapters → sections → subsections) are added to the second PDF as an
       incremental update — new objects and a new catalogue after the end of the file, the file before them untouched.
    4. Beside the PDF: <name>.sha256 — the hash of everything the PDF is made of (the Markdown, the pictures, this
       tool); tests/core/test_manual_pdf.py says when the PDF is older than its sources.
§4 SPECIFICATION
    python tools/manual_pdf.py [--lang ru] [--html FILE] [--out FILE]
        --html FILE  only write the HTML of the book (to look at it in a browser); no PDF.
    Needs PySide6 with QtWebEngine (PySide6-Addons, in requirements.txt). Runs without a screen.
    sources_hash(lang) -> str;  to_html(markdown, lang, version, pages=None) -> (html, headings);
    destinations(pdf_bytes) -> {name: page index from 0};  add_outline(pdf_bytes, headings) -> bytes.
§6 NOTES
    Chromium writes PDF 1.4 with a plain cross-reference table, every object at the top level (Skia's PDF back end);
    destinations() and add_outline() read only that form and raise ValueError on anything else.
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / 'docs' / 'manual'
FONTS = ROOT / 'assets' / 'fonts'
TITLES = {'ru': 'Руководство пользователя', 'en': 'User manual', 'zh': '用户手册'}
WORDS = {
    'ru': {'contents': 'Содержание', 'figure': 'Рисунок', 'table': 'Таблица', 'version': 'Версия',
           'appendix': 'Приложение', 'chapter': 'Глава', 'program': 'Азимут',
           'motto': 'Учебная программа по квантовой химии', 'header': 'Азимут',
           'sections': (('Атлас', 'теория: 56 интерактивных тем'), ('Компас', 'молекулы и кристаллы'),
                        ('Секстант', 'подготовка и запуск расчётов'), ('Спектр', 'разбор результатов'))},
    'en': {'contents': 'Contents', 'figure': 'Figure', 'table': 'Table', 'version': 'Version',
           'appendix': 'Appendix', 'chapter': 'Chapter', 'program': 'Azimuth',
           'motto': 'A teaching program for quantum chemistry', 'header': 'Azimuth',
           'sections': (('Atlas', 'theory: 56 interactive topics'), ('Compass', 'molecules and crystals'),
                        ('Sextant', 'setting up and running calculations'), ('Spectrum', 'reading the results'))},
    'zh': {'contents': '目录', 'figure': '图', 'table': '表', 'version': '版本',
           'appendix': '附录', 'chapter': '第', 'chapter_end': '章', 'program': '方位',
           'motto': '量子化学教学程序', 'header': '方位',
           'sections': (('图谱', '理论：56 个交互主题'), ('罗盘', '分子与晶体'),
                        ('六分仪', '准备并运行计算'), ('光谱', '解读结果'))},
}
# the page of the edition: the licence and the reference, in the language of the book
EDITION = {
    'ru': ('<p><b>«Азимут» (Azimuth). {title}.</b> Версия программы {version}.</p>'
           '<p>© 2026 С. А. Собалев. Программа распространяется по академической лицензии «Азимута» (файл LICENSE): '
           'свободно для преподавания, обучения и некоммерческих исследований с обязательной ссылкой на программу; '
           'коммерческое использование — с письменного разрешения автора.</p>'
           '<p><b>Как сослаться.</b> Собалев С. А. Азимут (Azimuth): учебная программа для квантово-химических '
           'расчётов. Версия {version}. 2026. URL: https://azimuth-chem.com</p>'
           '<p>Расчётные программы (ORCA, Gaussian, xtb и другие) в «Азимут» не входят и распространяются на условиях '
           'своих лицензий. Названия программ и компаний принадлежат их владельцам.</p>'
           '<p>Вопросы и сообщения об ошибках: contact@azimuth-chem.com</p>'),
    'en': ('<p><b>Azimuth («Азимут»). {title}.</b> Program version {version}.</p>'
           '<p>© 2026 S. A. Sobalev. The program is distributed under the Azimuth Academic License (the file LICENSE): '
           'free for teaching, learning and non-commercial research, with a reference to the program; commercial use '
           'only with the written permission of the author.</p>'
           '<p><b>How to cite.</b> Sobalev S. A. Azimuth: a teaching program for quantum-chemical calculations. '
           'Version {version}. 2026. URL: https://azimuth-chem.com</p>'
           '<p>The calculation programs (ORCA, Gaussian, xtb and others) are not part of Azimuth and are distributed '
           'under their own licenses. The names of programs and companies belong to their owners.</p>'
           '<p>Questions and bug reports: contact@azimuth-chem.com</p>'),
    'zh': ('<p><b>“方位”（Azimuth）。{title}。</b>程序版本 {version}。</p>'
           '<p>© 2026 S. A. Sobalev。本程序依据“方位”学术许可证（LICENSE 文件）发布：可免费用于教学、学习和非商业研究，'
           '但须引用本程序；商业使用须经作者书面许可。</p>'
           '<p><b>如何引用。</b>Sobalev S. A. Azimuth: a teaching program for quantum-chemical calculations. '
           'Version {version}. 2026. URL: https://azimuth-chem.com</p>'
           '<p>计算程序（ORCA、Gaussian、xtb 等）不包含在“方位”中，按其各自的许可证发布。程序和公司名称归其所有者所有。</p>'
           '<p>问题与错误报告：contact@azimuth-chem.com</p>'),
}
# Chinese text needs a CJK font of the system (Inter and Golos have none): PingFang on macOS, YaHei on Windows
CJK_FONTS = "'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans CJK SC', 'Source Han Sans SC'"
APPENDIX_LETTERS = 'АБВГДЕЖИКЛМН'
PAGE_MARGINS_MM = (18, 20, 20, 20)  # top, right, bottom, left — the room of the running header and the page number


def output(lang):
    return MANUAL / f'Azimuth-manual-{lang}.pdf'


def sources(lang):
    """The files the book is made of, in a fixed order."""
    files = [MANUAL / f'{lang}.md', Path(__file__).resolve()]
    # the pictures this book shows (each language has its own: NAME.jpg, NAME-en.jpg, NAME-zh.jpg) — a new picture of
    # one book does not make the others old
    text = (MANUAL / f'{lang}.md').read_text(encoding='utf-8') if files[0].is_file() else ''
    shown = {MANUAL / name for name in re.findall(r'!\[[^\]]*\]\((img/[^)\s]+)\)', text)}
    files += sorted(p for p in shown if p.is_file())
    files += sorted(FONTS.glob('Inter-*.otf')) + sorted(FONTS.glob('GolosText-*.ttf'))
    return files


def sources_hash(lang):
    digest = hashlib.sha256()
    for path in sources(lang):
        digest.update(path.relative_to(ROOT).as_posix().encode('utf-8') + b'\0')
        data = path.read_bytes()
        if path.suffix in ('.md', '.py'):  # the same text on Windows (a checkout with CRLF) and on macOS
            data = data.replace(b'\r\n', b'\n')
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


# ---------------------------------------------------------------- Markdown → HTML

def inline(text):
    """**bold**, *italic*, `code`, [text](url) of one paragraph → HTML (the text escaped)."""
    codes = []

    def keep(match):
        codes.append(match.group(1))
        return f'\x00{len(codes) - 1}\x00'

    text = re.sub(r'`([^`]+)`', keep, text)
    text = html_lib.escape(text, quote=False)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', text)

    def link(match):
        label, url = match.group(1), html_lib.unescape(match.group(2))
        return f'<a href="{html_lib.escape(url)}">{label}</a>'

    text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, text)
    def code(match):  # a short code stays on one line, a long one (a command) may break
        value = codes[int(match.group(1))]
        cls = ' class="long"' if len(value) > 22 else ''
        return f'<code{cls}>' + html_lib.escape(value, quote=False) + '</code>'

    return re.sub(r'\x00(\d+)\x00', code, text)


def slug(number):
    """The id of a heading: ASCII only — Chromium writes other letters of a named destination escaped, and an
    appendix «А» would not be found by its name."""
    return 'h-' + ''.join(c if c.isascii() and c.isalnum() else '-' if c == '.' else f'u{ord(c):x}' for c in number)


class Heading:
    def __init__(self, level, number, title, ident):
        self.level, self.number, self.title, self.id = level, number, title, ident

    def __repr__(self):
        return f'Heading({self.level}, {self.number!r}, {self.title!r})'


def _table(rows, caption):
    def cells(line):
        line = line.strip()
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]
        return [c.strip() for c in re.split(r'(?<!\\)\|', line)]

    head, body = cells(rows[0]), [cells(r) for r in rows[2:]]
    aligns = []
    for spec in cells(rows[1]):
        aligns.append('right' if spec.endswith(':') and not spec.startswith(':') else
                      'center' if spec.startswith(':') and spec.endswith(':') else '')
    out = ['<table>']
    if caption:
        out.append(f'<caption>{caption}</caption>')
    out.append('<thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr></thead><tbody>')
    for row in body:
        cells_html = []
        for i, c in enumerate(row):
            align = aligns[i] if i < len(aligns) else ''
            style = f' style="text-align:{align}"' if align else ''
            cells_html.append(f'<td{style}>{inline(c)}</td>')
        out.append('<tr>' + ''.join(cells_html) + '</tr>')
    out.append('</tbody></table>')
    return '\n'.join(out)


def body_html(markdown, lang):
    """The HTML of the body of the book and its headings (chapters, sections, subsections) in order."""
    words = WORDS.get(lang, WORDS['ru'])
    lines = markdown.replace('\r\n', '\n').split('\n')
    out, headings = [], []
    chapter, section, subsection, appendix = 0, 0, 0, 0
    chapter_label = ''
    figures = tables = 0
    paragraph, items, list_kind, quote = [], [], None, []
    pending_caption = None
    i = 0

    def flush_paragraph():
        nonlocal figures
        if not paragraph:
            return
        text = ' '.join(s.strip() for s in paragraph)
        paragraph.clear()
        image = re.fullmatch(r'!\[([^\]]*)\]\(([^)\s]+)\)', text)
        if image:
            figures += 1
            caption = inline(image.group(1))
            number = f'{chapter_label}.{figures}' if chapter_label else str(figures)
            out.append(f'<figure><img src="{html_lib.escape(image.group(2))}" alt="">'
                       f'<figcaption><span class="fig-no">{words["figure"]} {number}.</span> {caption}</figcaption>'
                       '</figure>')
            return
        out.append(f'<p>{inline(text)}</p>')

    def flush_list():
        nonlocal items, list_kind
        if not items:
            return
        tag = 'ol' if list_kind == 'ol' else 'ul'
        html_items = []
        for item in items:
            parts = '\n'.join(item).split('\n\n')
            html_items.append('<li>' + ''.join(
                (f'<p>{inline(" ".join(p.split()))}</p>' if k else inline(' '.join(p.split())))
                for k, p in enumerate(parts) if p.strip()) + '</li>')
        out.append(f'<{tag}>' + ''.join(html_items) + f'</{tag}>')
        items, list_kind = [], None

    def flush_quote():
        if not quote:
            return
        text = ' '.join(s.strip() for s in quote)
        quote.clear()
        kind = 'note'
        if re.match(r'\*\*(Внимание|Важно|Warning|Important|注意|重要)', text):
            kind = 'warning'
        elif re.match(r'\*\*(Совет|Подсказка|Tip|Hint|提示|技巧)', text):
            kind = 'tip'
        out.append(f'<aside class="{kind}"><p>{inline(text)}</p></aside>')

    def flush_all():
        flush_paragraph()
        flush_list()
        flush_quote()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith('```'):
            flush_all()
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                block.append(lines[i])
                i += 1
            out.append('<pre>' + html_lib.escape('\n'.join(block)) + '</pre>')
            i += 1
            continue
        heading = re.match(r'(#{1,4})\s+(.*)', line)
        if heading:
            flush_all()
            level, title = len(heading.group(1)), heading.group(2).strip()
            if level == 1:
                i += 1
                continue  # the title of the book is its title page
            if level == 2:
                figures = tables = 0
                section = subsection = 0
                match = re.match(r'(?:Приложение|Appendix|附录)\s*([^\s.。]+?)[.。]\s*(.*)', title)
                if match:
                    appendix += 1
                    chapter_label = match.group(1)
                    title = match.group(2)
                    number = chapter_label
                    label = f'{words["appendix"]} {chapter_label}'
                else:
                    chapter += 1
                    chapter_label = str(chapter)
                    number = chapter_label
                    label = (f'{words["chapter"]} {chapter_label} {words["chapter_end"]}' if 'chapter_end' in words
                             else f'{words["chapter"]} {chapter_label}')
                h = Heading(2, number, title, slug('c' + number))
                headings.append(h)
                if any(x.level == 2 for x in headings[:-1]):
                    out.append('</section>')
                out.append(f'<section class="chapter"><h2 id="{h.id}"><span class="label"><a href="#{h.id}">{label}</a></span>'
                           f'{inline(title)}</h2>')
            elif level == 3:
                section += 1
                subsection = 0
                number = f'{chapter_label}.{section}'
                h = Heading(3, number, title, slug('s' + number))
                headings.append(h)
                out.append(f'<h3 id="{h.id}"><a class="no" href="#{h.id}">{number}</a>{inline(title)}</h3>')
            else:
                subsection += 1
                number = f'{chapter_label}.{section}.{subsection}'
                h = Heading(4, number, title, slug('u' + number))
                headings.append(h)
                # the number links to its own heading: Chromium writes a named destination only for the target of a
                # link, and the subsections are not in the contents
                out.append(f'<h4 id="{h.id}"><a class="no" href="#{h.id}">{number}</a>{inline(title)}</h4>')
            i += 1
            continue
        if stripped.startswith('|') and i + 1 < len(lines) and re.match(r'\s*\|?\s*:?-{2,}', lines[i + 1]):
            flush_all()
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i])
                i += 1
            caption = None
            if pending_caption is not None:
                tables += 1
                number = f'{chapter_label}.{tables}' if chapter_label else str(tables)
                caption = f'<span class="tab-no">{words["table"]} {number}.</span> {inline(pending_caption)}'
            pending_caption = None
            out.append(_table(rows, caption))
            continue
        caption = re.match(r'(?:Таблица|Table|表)[:：]\s*(.+)', stripped)
        if caption:  # the caption of the table that follows (blank lines between them allowed)
            following = i + 1
            while following < len(lines) and not lines[following].strip():
                following += 1
            if following < len(lines) and lines[following].strip().startswith('|'):
                flush_all()
                pending_caption = caption.group(1)
                i = following
                continue
        if stripped.startswith('>'):
            flush_paragraph()
            flush_list()
            quote.append(stripped[1:].strip())
            i += 1
            continue
        item = re.match(r'(\d+)\.\s+(.*)|[-*]\s+(.*)', line)
        if item and not line.startswith((' ', '\t')):
            flush_paragraph()
            flush_quote()
            kind = 'ol' if item.group(1) else 'ul'
            if list_kind and kind != list_kind:
                flush_list()
            list_kind = kind
            items.append([item.group(2) if item.group(1) else item.group(3)])
            i += 1
            continue
        if items and line.startswith((' ', '\t')) and stripped:
            items[-1].append(stripped)
            i += 1
            continue
        if items and not stripped:
            # a blank line inside a list: the list goes on when the next line is indented or is the next item
            following = lines[i + 1] if i + 1 < len(lines) else ''
            if following.startswith(('   ', '\t')):
                items[-1].append('')
                i += 1
                continue
            if re.match(r'(\d+)\.\s+|[-*]\s+', following):
                i += 1
                continue
            flush_list()
            i += 1
            continue
        if not stripped:
            flush_all()
            i += 1
            continue
        flush_list()
        flush_quote()
        paragraph.append(line)
        i += 1
    flush_all()
    if any(h.level == 2 for h in headings):
        out.append('</section>')
    return '\n'.join(out), headings


def _font_faces():
    faces = []
    for name, weight, style in (('Regular', 400, 'normal'), ('Italic', 400, 'italic'), ('Medium', 500, 'normal'),
                                ('SemiBold', 600, 'normal'), ('Bold', 700, 'normal')):
        path = FONTS / f'Inter-{name}.otf'
        if path.exists():
            faces.append(f"@font-face {{ font-family: 'Inter Manual'; src: url('{path.as_uri()}'); "
                         f"font-weight: {weight}; font-style: {style}; }}")
    for name, weight in (('Medium', 500), ('SemiBold', 600)):
        path = FONTS / f'GolosText-{name}.ttf'
        if path.exists():
            faces.append(f"@font-face {{ font-family: 'Golos Manual'; src: url('{path.as_uri()}'); "
                         f"font-weight: {weight}; }}")
    return '\n'.join(faces)


STYLE = """
@page {
  size: A4;
  @top-left { content: "%(header)s"; font: 500 7.5pt 'Inter Manual', sans-serif; color: #8a94a6;
              vertical-align: bottom; padding-bottom: 4mm; }
  @top-right { content: "%(version)s"; font: 500 7.5pt 'Inter Manual', sans-serif; color: #8a94a6;
               vertical-align: bottom; padding-bottom: 4mm; }
  @bottom-center { content: counter(page); font: 500 8.5pt 'Inter Manual', sans-serif; color: #44506a;
                   vertical-align: top; padding-top: 5mm; }
}
@page cover { @top-left { content: none; } @top-right { content: none; } @bottom-center { content: none; } }
@page front { @top-left { content: none; } @top-right { content: none; } }
:root { --accent: #1f5fae; --ink: #1d2433; --soft: #5b667a; --rule: #d5dbe6; --note: #eef4fc; --warn: #fdf3e7;
        --tip: #eef8f1; }
html { font-family: 'Inter Manual', 'Inter', 'Helvetica Neue', Arial, sans-serif; font-size: 9.6pt;
       line-height: 1.47; color: var(--ink); -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; hyphens: auto; -webkit-hyphens: auto; text-align: justify; font-feature-settings: "tnum" 0; }
p { margin: 0 0 2.4mm; orphans: 3; widows: 3; }
a { color: var(--accent); text-decoration: none; }
strong { font-weight: 600; }
code { font-family: 'SF Mono', Menlo, Consolas, monospace; font-size: 0.9em; background: #f1f3f7;
       padding: 0.05em 0.3em; border-radius: 2px; hyphens: none; white-space: nowrap; }
code.long { white-space: normal; overflow-wrap: anywhere; }
pre { font-family: 'SF Mono', Menlo, Consolas, monospace; font-size: 8pt; line-height: 1.4; background: #f4f6fa;
      border-left: 2px solid var(--rule); padding: 2.5mm 3.5mm; white-space: pre-wrap; text-align: left;
      break-inside: avoid; margin: 0 0 3mm; }
ul, ol { margin: 0 0 2.6mm; padding-left: 6mm; }
li { margin: 0 0 1.1mm; }
li > p { margin: 1.2mm 0 0; }
ol > li::marker { font-weight: 600; color: var(--accent); }
ul > li::marker { color: var(--accent); }

/* the cover */
.cover { page: cover; height: 257mm; position: relative; text-align: left; break-after: page; }
.cover .band { position: absolute; left: -20mm; right: -20mm; top: -18mm; height: 120mm;
               background: linear-gradient(160deg, #0f2747 0%%, #1f4f8f 70%%, #2a6cc2 100%%); }
.cover .icon { position: absolute; left: 0; top: 18mm; width: 30mm; height: 30mm; border-radius: 7mm;
               box-shadow: 0 2mm 6mm rgba(0,0,0,.25); }
.cover h1 { position: absolute; left: 0; top: 56mm; margin: 0; font-family: 'Golos Manual', 'Inter Manual', sans-serif;
            font-weight: 600; font-size: 40pt; letter-spacing: -0.5pt; color: #fff; }
.cover .what { position: absolute; left: 0; top: 76mm; color: #cfe0f7; font-size: 13pt; font-weight: 500; }
.cover .book { position: absolute; left: 0; top: 112mm; font-family: 'Golos Manual', 'Inter Manual', sans-serif;
               font-size: 24pt; font-weight: 600; color: var(--ink); }
.cover .ver { position: absolute; left: 0; top: 126mm; font-size: 11pt; color: var(--soft); }
.cover .sections { position: absolute; left: 0; right: 0; top: 150mm; display: flex; gap: 4mm; }
.cover .sections div { flex: 1; border-top: 2px solid var(--accent); padding-top: 2.5mm; font-size: 8.5pt;
                       color: var(--soft); text-align: left; hyphens: manual; }
.cover .sections b { display: block; color: var(--ink); font-size: 10pt; font-weight: 600; margin-bottom: 1mm; }
.cover .foot { position: absolute; left: 0; right: 0; bottom: 0; font-size: 8pt; color: var(--soft);
               border-top: 1px solid var(--rule); padding-top: 3mm; text-align: left; }

/* the page after the cover: the edition, the license, how to cite */
.edition { page: front; break-after: page; font-size: 8.5pt; color: var(--soft); padding-top: 150mm; text-align: left; }
.edition p { margin-bottom: 2mm; }
.edition b { color: var(--ink); }

/* the table of contents */
.toc { page: front; break-after: page; }
.toc h2 { font-family: 'Golos Manual', 'Inter Manual', sans-serif; font-size: 20pt; font-weight: 600; margin: 0 0 7mm;
          color: var(--ink); }
.toc ol { list-style: none; padding: 0; margin: 0; }
.toc li { margin: 0; text-align: left; hyphens: manual; }
.toc .c { margin-top: 2.6mm; font-weight: 600; font-size: 10pt; break-after: avoid; }
.toc .s { font-size: 9pt; padding-left: 8.5mm; }
.toc a { color: inherit; display: flex; align-items: baseline; }
.toc .n { flex: 0 0 auto; min-width: 8.5mm; color: var(--accent); }
.toc .s .n { min-width: 10mm; color: var(--soft); }
.toc .t { flex: 0 1 auto; }
.toc .dots { flex: 1 1 auto; border-bottom: 1px dotted #b6bfcd; margin: 0 1.5mm; transform: translateY(-0.8mm); min-width: 4mm; }
.toc .p { flex: 0 0 9mm; text-align: right; font-variant-numeric: tabular-nums; }

/* chapters */
section.chapter { break-before: page; }
h2 { font-family: 'Golos Manual', 'Inter Manual', sans-serif; font-weight: 600; font-size: 21pt; line-height: 1.15;
     margin: 6mm 0 8mm; color: var(--ink); text-align: left; hyphens: manual; padding-bottom: 4mm;
     border-bottom: 2px solid var(--accent); }
h2 .label { display: block; font-family: 'Inter Manual', sans-serif; font-size: 9pt; font-weight: 600;
            letter-spacing: 1.2pt; text-transform: uppercase; color: var(--accent); margin-bottom: 2.5mm; }
h3 { font-size: 12.5pt; font-weight: 600; margin: 7mm 0 2.8mm; color: var(--ink); text-align: left; hyphens: manual;
     break-after: avoid; }
h4 { font-size: 10.3pt; font-weight: 600; margin: 5mm 0 2mm; color: var(--ink); text-align: left; hyphens: manual;
     break-after: avoid; }
h3 .no, h4 .no { color: var(--accent); margin-right: 2.6mm; font-variant-numeric: tabular-nums; }
h2 .label a { color: inherit; }
h3 + p, h4 + p { break-before: avoid; }

/* figures, tables, notes */
figure { margin: 4mm 0 5mm; break-inside: avoid; text-align: center; }
figure img { max-width: 100%%; max-height: 118mm; border: 1px solid var(--rule); border-radius: 1.5mm; }
figcaption { font-size: 8.3pt; color: var(--soft); margin-top: 2mm; text-align: center; hyphens: manual; }
.fig-no, .tab-no { font-weight: 600; color: var(--ink); }
table { width: 100%%; border-collapse: collapse; margin: 2mm 0 4.5mm; font-size: 8.5pt; line-height: 1.38;
        text-align: left; hyphens: auto; break-inside: auto; }
caption { caption-side: top; text-align: left; font-size: 8.3pt; color: var(--soft); padding-bottom: 1.6mm; }
thead { display: table-header-group; }
th { font-weight: 600; background: #eef2f8; border-bottom: 1px solid #b9c4d6; padding: 1.4mm 2mm; vertical-align: bottom; }
td { border-bottom: 1px solid var(--rule); padding: 1.3mm 2mm; vertical-align: top; }
tr { break-inside: avoid; }
aside { margin: 2mm 0 3.5mm; padding: 2.4mm 3.5mm; border-left: 2.5px solid var(--accent); background: var(--note);
        border-radius: 0 1.5mm 1.5mm 0; break-inside: avoid; font-size: 9pt; }
aside p { margin: 0; }
aside.warning { border-left-color: #d9822b; background: var(--warn); }
aside.tip { border-left-color: #2f9e60; background: var(--tip); }
"""


def to_html(markdown, lang, version, pages=None, edition_date=''):
    """The whole book as one HTML page and its headings. pages: {heading id: page number} for the contents (else
    «000» — the room of three digits, so that the numbers of the second print take the same room)."""
    words = WORDS.get(lang, WORDS['ru'])
    body, headings = body_html(markdown, lang)
    title = TITLES.get(lang, TITLES['ru'])
    toc = ['<nav class="toc"><h2>' + words['contents'] + '</h2><ol>']
    for h in headings:
        if h.level > 3:
            continue
        page = str(pages.get(h.id, '')) if pages else '000'
        cls = 'c' if h.level == 2 else 's'
        number = (words['appendix'] + ' ' + h.number + '.') if (h.level == 2 and not h.number.isdigit()) else h.number
        toc.append(f'<li class="{cls}"><a href="#{h.id}"><span class="n">{html_lib.escape(number)}</span>'
                   f'<span class="t">{inline(h.title)}</span><span class="dots"></span>'
                   f'<span class="p">{page}</span></a></li>')
    toc.append('</ol></nav>')
    icon = ROOT / 'assets' / 'app-icon' / 'azimuth-256.png'
    sections = words['sections']
    cover = (
        '<div class="cover"><div class="band"></div>'
        + (f'<img class="icon" src="{icon.as_uri()}" alt="">' if icon.exists() else '')
        + f'<h1>{words["program"]}</h1><div class="what">{words["motto"]}</div>'
        + f'<div class="book">{title}</div><div class="ver">{words["version"]} {version}'
        + (f' · {edition_date}' if edition_date else '') + '</div>'
        + '<div class="sections">' + ''.join(f'<div><b>{a}</b>{b}</div>' for a, b in sections) + '</div>'
        + '<div class="foot">azimuth-chem.com</div></div>')
    edition = '<div class="edition">' + EDITION.get(lang, EDITION['ru']).format(title=title, version=version) + '</div>'
    style = STYLE % {'header': f'{words["header"]} · {title}', 'version': f'{words["version"]} {version}'}
    if lang == 'zh':  # the Chinese letters come from a font of the system, after the Latin ones of Inter
        style = style.replace("'Inter Manual',", "'Inter Manual', " + CJK_FONTS + ",")
        style += '\nbody { text-align: left; hyphens: manual; -webkit-hyphens: manual; }\n'
    page = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{words["program"]} — {title}</title>'
            f'<style>{_font_faces()}\n{style}</style></head><body>{cover}{edition}{"".join(toc)}{body}</body></html>')
    return page, headings


# ---------------------------------------------------------------- PDF: destinations and bookmarks

_OBJ = re.compile(rb'(\d+) 0 obj\s*(.*?)\s*endobj', re.S)


def _objects(data):
    """{number: body} of the top-level objects (the last definition wins, as in a PDF with updates)."""
    return {int(m.group(1)): m.group(2) for m in _OBJ.finditer(data)}


def _trailer(data):
    at = data.rfind(b'trailer')
    if at < 0 or b'/Type /XRef' in data[-4096:]:
        raise ValueError('the PDF has no plain trailer (a cross-reference stream is not read here)')
    return data[at:]


def _ref(body, key):
    m = re.search(rb'/' + key + rb'\s+(\d+) 0 R', body)
    return int(m.group(1)) if m else None


def _pages(objects, node):
    body = objects[node]
    if re.search(rb'/Type\s*/Pages\b', body):
        kids = re.search(rb'/Kids\s*\[(.*?)\]', body, re.S)
        result = []
        for number in re.findall(rb'(\d+) 0 R', kids.group(1) if kids else b''):
            result += _pages(objects, int(number))
        return result
    return [node]


def destinations(data):
    """{name: page index from 0} of the named destinations of a PDF of Chromium (the /Dests of its catalogue)."""
    objects = _objects(data)
    root = _ref(_trailer(data), b'Root')
    if root is None or root not in objects:
        raise ValueError('no catalogue in the PDF')
    catalogue = objects[root]
    order = {page: index for index, page in enumerate(_pages(objects, _ref(catalogue, b'Pages')))}
    dests = _ref(catalogue, b'Dests')
    if dests is None:
        return {}
    found = {}
    for name, page in re.findall(rb'/([^\s/\[<>()]+)\s*\[\s*(\d+) 0 R', objects[dests]):
        found[name.decode('latin-1')] = order.get(int(page))
    return found


def _pdf_text(text):
    """A string of the PDF in UTF-16BE with its byte order mark (the titles of the bookmarks, any language)."""
    return b'<FEFF' + text.encode('utf-16-be').hex().upper().encode('ascii') + b'>'


def add_outline(data, headings, title=''):
    """The PDF with bookmarks of the headings (levels 2–4 nested), opened with the bookmarks shown; an incremental
    update: the bytes of data stay as they are, new objects follow them."""
    objects = _objects(data)
    trailer = _trailer(data)
    size = int(re.search(rb'/Size\s+(\d+)', trailer).group(1))
    root = _ref(trailer, b'Root')
    info = _ref(trailer, b'Info')
    startxref = int(re.findall(rb'startxref\s+(\d+)', data)[-1])
    catalogue = objects[root]
    # the tree: every heading under the last heading of a smaller level
    nodes = [{'h': h, 'kids': [], 'num': None} for h in headings]
    top, stack = [], []
    for node in nodes:
        while stack and stack[-1]['h'].level >= node['h'].level:
            stack.pop()
        (stack[-1]['kids'] if stack else top).append(node)
        stack.append(node)
    next_number = size
    outline_number = next_number
    next_number += 1
    for node in nodes:
        node['num'] = next_number
        next_number += 1
    new = {}

    def write_level(siblings, parent):
        for k, node in enumerate(siblings):
            h = node['h']
            label = f'{h.number} {h.title}' if h.number else h.title
            label = re.sub(r'[*`]', '', label)
            parts = [b'/Title ' + _pdf_text(label), b'/Parent %d 0 R' % parent,
                     b'/Dest /' + h.id.encode('ascii')]
            if k > 0:
                parts.append(b'/Prev %d 0 R' % siblings[k - 1]['num'])
            if k + 1 < len(siblings):
                parts.append(b'/Next %d 0 R' % siblings[k + 1]['num'])
            if node['kids']:
                parts.append(b'/First %d 0 R' % node['kids'][0]['num'])
                parts.append(b'/Last %d 0 R' % node['kids'][-1]['num'])
                # chapters open, sections closed: the reader sees the chapters and the sections of a chapter
                count = len(node['kids'])
                parts.append(b'/Count %d' % (count if h.level == 2 else -count))
            new[node['num']] = b'<<' + b'\n'.join(parts) + b'>>'
            write_level(node['kids'], node['num'])

    write_level(top, outline_number)
    new[outline_number] = (b'<</Type /Outlines' + (b' /First %d 0 R /Last %d 0 R' % (top[0]['num'], top[-1]['num'])
                                                    if top else b'') + b' /Count %d>>' % len(top))
    body = re.sub(rb'/Outlines\s+\d+ 0 R|/PageMode\s*/\w+', b'', catalogue).strip()
    if not body.startswith(b'<<') or not body.endswith(b'>>'):
        raise ValueError('an unexpected catalogue')
    new[root] = body[:-2] + b'\n/Outlines %d 0 R\n/PageMode /UseOutlines>>' % outline_number
    if title and info is not None and info in objects:
        info_body = re.sub(rb'/Title\s*(\(.*?\)|<[0-9A-Fa-f]*>)', b'', objects[info], flags=re.S).strip()
        new[info] = info_body[:-2] + b'\n/Title ' + _pdf_text(title) + b'>>'
    out = bytearray(data if data.endswith(b'\n') else data + b'\n')
    offsets = {}
    for number in sorted(new):
        offsets[number] = len(out)
        out += b'%d 0 obj\n' % number + new[number] + b'\nendobj\n'
    xref_at = len(out)
    out += b'xref\n'
    numbers = sorted(offsets)
    runs, start = [], None
    for index, number in enumerate(numbers):  # the runs of consecutive numbers: one subsection each
        if start is None:
            start = number
        if index + 1 == len(numbers) or numbers[index + 1] != number + 1:
            runs.append((start, number))
            start = None
    for first, last in runs:
        out += b'%d %d\n' % (first, last - first + 1)
        for number in range(first, last + 1):
            out += b'%010d 00000 n \n' % offsets[number]
    out += (b'trailer\n<</Size %d\n/Root %d 0 R' % (max(next_number, size), root)
            + (b'\n/Info %d 0 R' % info if info is not None else b'') + b'\n/Prev %d>>\n' % startxref)
    out += b'startxref\n%d\n%%%%EOF\n' % xref_at
    return bytes(out)


# ---------------------------------------------------------------- printing

def print_pdf(html_path, pdf_path, timeout=300):
    """The HTML file printed to PDF by the Chromium of Qt, A4 with the margins of PAGE_MARGINS_MM. Raises on failure."""
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu')
    from PySide6.QtCore import QMarginsF, QTimer, QUrl
    from PySide6.QtGui import QPageLayout, QPageSize
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    page = QWebEnginePage()
    page.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
    result = {}

    def loaded(ok):
        if not ok:
            result['error'] = 'the page did not load'
            app.quit()
            return
        top, right, bottom, left = PAGE_MARGINS_MM
        layout = QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
                             QMarginsF(left, top, right, bottom), QPageLayout.Unit.Millimeter)
        # the fonts and pictures are loaded with the page; a short pause lets the layout settle
        QTimer.singleShot(1500, lambda: page.printToPdf(str(pdf_path), layout))

    def printed(path, ok):
        result['ok'] = ok
        app.quit()

    page.loadFinished.connect(loaded)
    page.pdfPrintingFinished.connect(printed)
    if Path(pdf_path).exists():
        Path(pdf_path).unlink()
    page.load(QUrl.fromLocalFile(str(html_path)))
    QTimer.singleShot(timeout * 1000, app.quit)
    app.exec()
    if not result.get('ok') or not Path(pdf_path).exists():
        raise RuntimeError(result.get('error', 'Chromium did not print the PDF'))
    return Path(pdf_path).read_bytes()


def build(lang='ru', out=None, keep_html=None):
    sys.path.insert(0, str(ROOT))
    import azimuth

    version = azimuth.__version__
    markdown = (MANUAL / f'{lang}.md').read_text(encoding='utf-8')
    out = Path(out) if out else output(lang)
    work = out.with_suffix('.build.html')
    first_pdf = out.with_suffix('.pass1.pdf')
    try:
        html, headings = to_html(markdown, lang, version)
        work.write_text(html, encoding='utf-8')
        first = destinations(print_pdf(work, first_pdf))
        pages = {h.id: (first[h.id] + 1) for h in headings if first.get(h.id) is not None}
        missing = [h.number for h in headings if h.id not in pages]
        if missing:
            raise RuntimeError('no page found for the headings ' + ', '.join(missing[:10]))
        html, headings = to_html(markdown, lang, version, pages)
        work.write_text(html, encoding='utf-8')
        data = print_pdf(work, out)
        second = destinations(data)
        moved = [h.number for h in headings if second.get(h.id) is not None and second[h.id] + 1 != pages[h.id]]
        if moved:
            raise RuntimeError('the pages moved between the two prints: ' + ', '.join(moved[:10]))
        data = add_outline(data, headings, title=f'{WORDS.get(lang, WORDS["ru"])["program"]} {version} — {TITLES.get(lang, "")}')
        out.write_bytes(data)
        out.with_name(out.stem + '.sha256').write_text(sources_hash(lang) + '\n', encoding='utf-8')
        return out, len(_pages(_objects(data), _ref(_objects(data)[_ref(_trailer(data), b'Root')], b'Pages')))
    finally:
        first_pdf.unlink(missing_ok=True)
        if keep_html:
            work.replace(keep_html)
        else:
            work.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--lang', default='ru')
    parser.add_argument('--html', help='only write the HTML of the book to this file')
    parser.add_argument('--out')
    args = parser.parse_args(argv)
    if args.html:
        sys.path.insert(0, str(ROOT))
        import azimuth

        markdown = (MANUAL / f'{args.lang}.md').read_text(encoding='utf-8')
        html, headings = to_html(markdown, args.lang, azimuth.__version__)
        Path(args.html).write_text(html, encoding='utf-8')
        print(f'{args.html}: {len(headings)} headings')
        return 0
    path, pages = build(args.lang, args.out)
    print(f'{path}: {pages} pages')
    return 0


if __name__ == '__main__':
    sys.exit(main())
