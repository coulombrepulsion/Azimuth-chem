"""The book of the manual (tools/manual_pdf.py): the PDF is as new as its sources, every heading has its page and
bookmark, the numbering of chapters, appendices, figures and tables. Oracles: the PDF printed by Chromium
(docs/manual/Azimuth-manual-ru.pdf) and small Markdown texts with numbers counted by hand."""

import re

import pytest

from tools import manual_pdf


def test_the_book_is_as_new_as_its_sources():
    pdf = manual_pdf.output('ru')
    assert pdf.is_file(), 'нет docs/manual/Azimuth-manual-ru.pdf: .venv/bin/python tools/manual_pdf.py'
    recorded = pdf.with_name(pdf.stem + '.sha256').read_text(encoding='utf-8').strip()
    assert recorded == manual_pdf.sources_hash('ru'), (
        'руководство изменилось после сборки PDF: .venv/bin/python tools/manual_pdf.py')


def test_every_picture_of_the_manual_is_there_and_every_picture_there_is_used():
    # the three books, each with the pictures of the program in its language
    text = ''.join((manual_pdf.MANUAL / f'{lang}.md').read_text(encoding='utf-8') for lang in ('ru', 'en', 'zh'))
    used = set(re.findall(r'!\[[^\]]*\]\((img/[^)\s]+)\)', text))
    assert used and all((manual_pdf.MANUAL / name).is_file() for name in used)
    present = {'img/' + p.name for p in (manual_pdf.MANUAL / 'img').iterdir() if not p.name.startswith('.')}
    assert present == used  # no picture kept in the program that the book does not show


def test_every_heading_has_its_page_and_its_bookmark():
    data = manual_pdf.output('ru').read_bytes()
    _, headings = manual_pdf.to_html((manual_pdf.MANUAL / 'ru.md').read_text(encoding='utf-8'), 'ru', '0')
    pages = manual_pdf.destinations(data)
    assert len(headings) > 80 and all(pages.get(h.id) is not None for h in headings)
    chapters = [pages[h.id] for h in headings if h.level == 2]
    assert chapters == sorted(chapters) and len(set(chapters)) == len(chapters)  # one chapter a page at least
    assert b'/Type /Outlines' in data and b'/PageMode /UseOutlines' in data and b'/Prev ' in data


def test_the_numbers_of_chapters_appendices_figures_and_tables():
    markdown = '\n'.join([
        '# Книга', '', '## Первая', '', '### Раздел', '', '#### Подраздел', '', '![Окно](img/a.jpg)', '',
        'Таблица: Числа', '', '| a | b |', '|---|---:|', '| 1 | 2 |', '', '## Вторая', '', '### Раздел', '',
        '![Ещё](img/b.jpg)', '', '## Приложение А. Форматы', '', '### Ввод', '', 'Таблица: Форматы', '', '| x |',
        '|---|', '| y |', '', '> **Внимание.** Осторожно.', '', '1. Первый шаг', '2. Второй шаг', '',
    ])
    html, headings = manual_pdf.to_html(markdown, 'ru', '1.2.3')
    assert [(h.level, h.number, h.title) for h in headings] == [
        (2, '1', 'Первая'), (3, '1.1', 'Раздел'), (4, '1.1.1', 'Подраздел'), (2, '2', 'Вторая'), (3, '2.1', 'Раздел'),
        (2, 'А', 'Форматы'), (3, 'А.1', 'Ввод')]
    assert 'Рисунок 1.1.' in html and 'Рисунок 2.1.' in html and 'Таблица 1.1.' in html and 'Таблица А.1.' in html
    assert 'Приложение А' in html and '<aside class="warning">' in html and '<ol><li>Первый шаг</li>' in html
    assert 'text-align:right' in html  # the alignment of the column «---:»
    assert all(re.fullmatch(r'h-[A-Za-z0-9-]+', h.id) for h in headings)  # ASCII ids: Chromium escapes other letters
    assert html.count('<section class="chapter">') == html.count('</section>') == 3


def test_the_english_and_chinese_books_number_as_the_russian_one():
    # the words of the book in its language: «Chapter 1» / «第 1 章», «Appendix A» / «附录 A», «Table» / «表：», the
    # notes «Warning» / «注意» and «Tip» / «提示»; Chinese text needs a CJK font of the system
    en = '\n'.join(['# Book', '', '## First', '', '### Part', '', 'Table: Numbers', '', '| a |', '|---|', '| 1 |', '',
                    '> **Warning.** Careful.', '', '> **Tip.** Quick.', '', '## Appendix A. Formats', ''])
    html, headings = manual_pdf.to_html(en, 'en', '1')
    assert [(h.level, h.number) for h in headings] == [(2, '1'), (3, '1.1'), (2, 'A')]
    assert 'Chapter 1' in html and 'Appendix A' in html and 'Table 1.1.' in html and 'User manual' in html
    assert '<aside class="warning">' in html and '<aside class="tip">' in html and 'Version 1' in html
    zh = '\n'.join(['# 书', '', '## 第一', '', '表：数字', '', '| a |', '|---|', '| 1 |', '', '> **注意。** 小心。', '',
                    '> **提示。** 快。', '', '## 附录 A。格式', ''])
    html, headings = manual_pdf.to_html(zh, 'zh', '1')
    assert [(h.level, h.number, h.title) for h in headings] == [(2, '1', '第一'), (2, 'A', '格式')]
    assert '第 1 章' in html and '附录 A' in html and '表 1.1.' in html and '用户手册' in html
    assert '<aside class="warning">' in html and '<aside class="tip">' in html and 'PingFang SC' in html


def test_the_three_manuals_have_the_same_chapters_figures_and_tables():
    # the English and Chinese manuals are translations of the Russian one: the same headings, pictures and tables
    books = {lang: manual_pdf.to_html((manual_pdf.MANUAL / f'{lang}.md').read_text(encoding='utf-8'), lang, '0')
             for lang in ('ru', 'en', 'zh')}
    shape = {lang: ([(h.level, h.number if h.number.isdigit() or '.' in h.number else len(h.number)) for h in hs],
                    html.count('<figure>'), html.count('<caption>'))
             for lang, (html, hs) in books.items()}
    assert shape['en'] == shape['ru'] and shape['zh'] == shape['ru']
    pictures = {lang: sorted(re.findall(r'img/[\w-]+\.jpg', (manual_pdf.MANUAL / f'{lang}.md').read_text(encoding='utf-8')))
                for lang in ('ru', 'en', 'zh')}
    # the same pictures, each taken from the program in the language of its book
    assert sorted(p.replace('-en.jpg', '.jpg') for p in pictures['en']) == pictures['ru']
    assert sorted(p.replace('-zh.jpg', '.jpg') for p in pictures['zh']) == pictures['ru']
    assert not any(p.endswith(('-en.jpg', '-zh.jpg')) for p in pictures['ru'])
    assert all(p.endswith('-en.jpg') for p in pictures['en']) and all(p.endswith('-zh.jpg') for p in pictures['zh'])


def test_the_contents_take_the_room_of_three_digits_before_the_pages_are_known():
    markdown = '# К\n\n## Глава\n\n### Раздел\n'
    first, headings = manual_pdf.to_html(markdown, 'ru', '1')
    second, _ = manual_pdf.to_html(markdown, 'ru', '1', {h.id: 7 for h in headings})
    assert first.count('<span class="p">000</span>') == 2 and second.count('<span class="p">7</span>') == 2


def test_the_bookmarks_are_an_update_after_the_untouched_file():
    # a PDF of two pages and two named destinations, written by hand in the form of Chromium
    objects = [b'<</Type /Catalog /Pages 2 0 R /Dests 5 0 R>>', b'<</Type /Pages /Count 2 /Kids [3 0 R 4 0 R]>>',
               b'<</Type /Page /Parent 2 0 R>>', b'<</Type /Page /Parent 2 0 R>>',
               b'<</h-c1 [3 0 R /XYZ 0 800 0]\n/h-s1-1 [4 0 R /XYZ 0 500 0]>>']
    data = bytearray(b'%PDF-1.4\n')
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(data))
        data += b'%d 0 obj\n' % number + body + b'\nendobj\n'
    xref = len(data)
    data += b'xref\n0 6\n0000000000 65535 f \n' + b''.join(b'%010d 00000 n \n' % o for o in offsets)
    data += b'trailer\n<</Size 6 /Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n' % xref
    data = bytes(data)
    assert manual_pdf.destinations(data) == {'h-c1': 0, 'h-s1-1': 1}
    headings = [manual_pdf.Heading(2, '1', 'Глава', 'h-c1'), manual_pdf.Heading(3, '1.1', 'Раздел', 'h-s1-1')]
    updated = manual_pdf.add_outline(data, headings)
    assert updated.startswith(data)  # the file before the update is untouched
    tail = updated[len(data):]
    assert b'/Type /Outlines' in tail and b'/Prev %d' % xref in tail and b'/Dest /h-s1-1' in tail
    assert manual_pdf._pdf_text('1 Глава') in tail  # the title in UTF-16 with its byte order mark
    assert manual_pdf.destinations(updated) == {'h-c1': 0, 'h-s1-1': 1}  # the new catalogue keeps its destinations
    with pytest.raises(ValueError):
        manual_pdf.destinations(data.replace(b'trailer', b'xx').replace(b'%%EOF', b'/Type /XRef'))
