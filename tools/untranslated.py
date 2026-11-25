"""What waits for its translation (0.108.75+, the process agreed on the journal of Quill and the manual are
written in Russian with each version and translated at a release).

Prints, for English and Chinese: the versions of docs/journal/ru.md that docs/journal/<lang>.md lacks, and the items
of docs/manual/ru.md marked with a version (« ») whose mark is not in docs/manual/<lang>.md. Exit code 1
when something waits (for a check before a release), 0 when all is translated.

    python3 tools/untranslated.py # the list
    python3 tools/untranslated.py --text # with the Russian text to translate
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEAD = re.compile(r'^## (\d+\.\d+\.\d+)\b.*$', re.M)
MARK = re.compile(r'[(（](\d+\.\d+\.\d+)[)）;,；，]')  # «(как …)» too


def journal(lang):
    text = (ROOT / 'docs' / 'journal' / f'{lang}.md').read_text(encoding='utf-8')
    heads = list(HEAD.finditer(text))
    return {m[1]: text[m.end():heads[k + 1].start() if k + 1 < len(heads) else len(text)].strip()
            for k, m in enumerate(heads)}


def manual(lang):
    out = {}
    for line in (ROOT / 'docs' / 'manual' / f'{lang}.md').read_text(encoding='utf-8').split('\n'):
        if line.startswith('- '):
            for version in MARK.findall(line[:200]):
                out.setdefault(version, line)
    return out


def waiting(lang):
    """{'journal': {version: Russian text}, 'manual': {version: Russian item}} not yet in lang."""
    have_j, have_m = journal(lang), manual(lang)
    marks = set(MARK.findall((ROOT / 'docs' / 'manual' / f'{lang}.md').read_text(encoding='utf-8')))
    return {'journal': {v: t for v, t in journal('ru').items() if v not in have_j},
            'manual': {v: t for v, t in manual('ru').items() if v not in have_m and v not in marks}}


def main():
    text = '--text' in sys.argv
    found = False
    for lang in ('en', 'zh'):
        left = waiting(lang)
        for kind in ('journal', 'manual'):
            if left[kind]:
                found = True
                print(f'{lang} · {kind}: {len(left[kind])} — ' + ', '.join(left[kind]))
                if text:
                    for version, body in left[kind].items():
                        print(f'\n[{version}]\n{body}')
    if not found:
        print('Всё переведено.')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
