"""Publish the site to both places at once: the main site (www.azimuth-chem.com, Cloudflare Pages) and the
mirror for Russia (ru.azimuth-chem.com, Yandex Object Storage — the providers of Russia slow down Cloudflare).

§2 ALGORITHM
    Two builds of tools/build_atlas_site.py (the previews of a link need the address of their own copy; the answers of
    the Atlas are counted once — site/.answers — so the second build is quick): ~/azimuth-site for www and
    ~/azimuth-site-ru for the mirror; then «npx wrangler pages deploy» of the first (Node.js; «npx wrangler login» once)
    and tools/upload_site_yandex.py of the second (the static key in AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY).
§4 SPECIFICATION
    python tools/publish_site.py [--only www|ru] [--project azimuth-atlas] [--branch main] [--no-build] [--delete]
    --delete: the mirror also deletes the files the new build no longer has (the key needs the role
    storage.editor; Cloudflare Pages replaces the whole site by itself).
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

PLACES = {'www': ('https://www.azimuth-chem.com/', Path.home() / 'azimuth-site'),
          'ru': ('https://ru.azimuth-chem.com/', Path.home() / 'azimuth-site-ru')}


def run(command):
    print('$', ' '.join(str(c) for c in command), flush=True)
    return subprocess.run([str(c) for c in command], cwd=ROOT).returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--only', choices=sorted(PLACES), help='only one of the two places')
    parser.add_argument('--project', default='azimuth-atlas', help='the project of Cloudflare Pages')
    parser.add_argument('--branch', default='main', help='the production branch of that project')
    parser.add_argument('--no-build', action='store_true', help='publish the folders built before')
    parser.add_argument('--delete', action='store_true', help='the mirror: delete the files the build no longer has')
    args = parser.parse_args(argv)
    places = [args.only] if args.only else ['www', 'ru']
    if 'www' in places and shutil.which('npx') is None:
        sys.exit('Нет npx (Node.js): brew install node, затем npx wrangler login — или --only ru')
    if 'ru' in places and not (os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY')):
        sys.exit('Для зеркала нужен ключ Яндекса: export AWS_ACCESS_KEY_ID=… AWS_SECRET_ACCESS_KEY=… — или --only www')
    for place in places:
        url, out = PLACES[place]
        if not args.no_build and run([sys.executable, 'tools/build_atlas_site.py', '--out', out, '--url', url]):
            sys.exit(f'Сборка для {url} не удалась')
    if 'www' in places:
        out = PLACES['www'][1]
        if run(['npx', '--yes', 'wrangler', 'pages', 'deploy', out, '--project-name', args.project,
                '--branch', args.branch, '--commit-dirty=true']):
            sys.exit('Cloudflare: wrangler не выложил сайт (npx wrangler login?)')
    if 'ru' in places:
        if run([sys.executable, 'tools/upload_site_yandex.py', PLACES['ru'][1]] + (['--delete'] if args.delete else [])):
            sys.exit('Яндекс: загрузка не удалась')
    print('Опубликовано: ' + ', '.join(PLACES[p][0] for p in places))
    return 0


if __name__ == '__main__':
    sys.exit(main())
