"""Upload the built site to Yandex Object Storage — the mirror for Russia.

§1 THEORY
    The site lives behind Cloudflare (www.azimuth-chem.com), and the providers of Russia slow down the connections to
    the addresses of Cloudflare since 2025 (about 16 KB, then the connection stalls): the pages open only with a VPN.
    A copy in a bucket of Yandex Object Storage with «Веб-сайт → Хостинг», reached by a DNS record without the proxy of
    Cloudflare (CNAME ru → ru.azimuth-chem.com.website.yandexcloud.net, «DNS only»), is not slowed down. Object Storage
    speaks the API of Amazon S3: each file is a PUT of the object signed by AWS Signature Version 4 (region
    ru-central1) with the static access key of a service account (role storage.uploader).
§2 ALGORITHM The files of the folder (made by tools/build_atlas_site.py --url https://ru.azimuth-chem.com/) are compared
    with the objects of the bucket by their MD5 (the ETag of a simple PUT; ListObjectsV2) and only the changed ones are
    sent, each with its type (Content-Type: .wasm — application/wasm, the texts in UTF-8: the hosting sends the type
    kept with the object, it has no _headers file) and Cache-Control (pages, sw.js, site-files.json — always asked anew;
    the runtime of Python, fonts and pictures — a day). Objects the folder no longer has are listed, not deleted
    (storage.uploader may not delete; «--delete» for a key with storage.editor).
§4 SPECIFICATION
    python tools/upload_site_yandex.py FOLDER [--bucket ru.azimuth-chem.com] [--delete] [--dry-run]
    The key: the environment AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (never written into a file of the program).
    sign(method, url, headers, payload_hash, key_id, secret, when, region='ru-central1') -> the headers with
    Authorization; content_type(name); cache_control(name).
§7 TESTS
    tests/core/test_upload_site.py — the signature of the example of the documentation of Amazon S3 (GET with Range),
    the types and the plan of the upload on a folder without a network.
"""

import argparse
import hashlib
import hmac
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ENDPOINT = 'https://storage.yandexcloud.net'
REGION = 'ru-central1'
BUCKET = 'ru.azimuth-chem.com'
SKIP = ('_redirects', '_headers', '.nojekyll', '.DS_Store')  # the files of Cloudflare Pages and GitHub Pages
TYPES = {'.wasm': 'application/wasm', '.whl': 'application/zip', '.js': 'text/javascript', '.mjs': 'text/javascript',
         '.json': 'application/json', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.woff2': 'font/woff2',
         '.zip': 'application/zip', '.ico': 'image/x-icon', '.txt': 'text/plain', '.md': 'text/markdown',
         '.html': 'text/html', '.css': 'text/css', '.xml': 'application/xml', '.tar': 'application/x-tar'}
TEXT = ('text/', 'application/json', 'application/xml', 'image/svg+xml')
FRESH = ('.html', '.json', '.js', '.css')  # asked anew each time (a copy kept is only checked, 304 when the same):
# a new build must be seen at once (sw.js keeps its own copies). Scripts and styles had a day of keeping
# (max-age=86400), and a new rail.js was not seen after a publication


def content_type(name):
    kind = TYPES.get(Path(name).suffix.lower()) or mimetypes.guess_type(name)[0] or 'application/octet-stream'
    return kind + '; charset=utf-8' if kind.startswith(TEXT) else kind


def cache_control(name):
    if name.startswith('atlas/assets/pyodide-'):  # the runtime: its version is in its address, it never changes there
        return 'public, max-age=86400'
    if Path(name).name == 'sw.js' or Path(name).suffix.lower() in FRESH:
        return 'no-cache'
    return 'public, max-age=86400'


def _hmac(key, text):
    return hmac.new(key, text.encode('utf-8'), hashlib.sha256).digest()


def sign(method, url, headers, payload_hash, key_id, secret, when, region=REGION, service='s3'):
    """AWS Signature Version 4: the headers given (any case) with x-amz-date, x-amz-content-sha256 and Authorization."""
    parts = urllib.parse.urlsplit(url)
    stamp, day = when.strftime('%Y%m%dT%H%M%SZ'), when.strftime('%Y%m%d')
    all_headers = {k.lower(): str(v).strip() for k, v in headers.items()}
    all_headers.update({'host': parts.netloc, 'x-amz-date': stamp, 'x-amz-content-sha256': payload_hash})
    names = sorted(all_headers)
    query = sorted(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
    canonical_query = '&'.join(f'{urllib.parse.quote(k, safe="-_.~")}={urllib.parse.quote(v, safe="-_.~")}'
                               for k, v in query)
    canonical = '\n'.join([method, parts.path or '/', canonical_query,
                           ''.join(f'{n}:{all_headers[n]}\n' for n in names), ';'.join(names), payload_hash])
    scope = f'{day}/{region}/{service}/aws4_request'
    to_sign = '\n'.join(['AWS4-HMAC-SHA256', stamp, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    key = _hmac(_hmac(_hmac(_hmac(('AWS4' + secret).encode(), day), region), service), 'aws4_request')
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    all_headers['authorization'] = (f'AWS4-HMAC-SHA256 Credential={key_id}/{scope}, SignedHeaders={";".join(names)}, '
                                    f'Signature={signature}')
    return all_headers


def object_url(bucket, key='', query=''):
    path = '/' + bucket + ('/' + urllib.parse.quote(key, safe='/-_.~') if key else '/')
    return ENDPOINT + path + ('?' + query if query else '')


def tls_context():
    """The certificates of the authorities: the Python of python.org on macOS has none of its own until «Install
    Certificates.command» is run (CERTIFICATE_VERIFY_FAILED) — then those of certifi, or
    the copy of certifi inside pip (every .venv has pip)."""
    import ssl

    default = ssl.get_default_verify_paths()
    if default.cafile and Path(default.cafile).is_file():
        return ssl.create_default_context()
    for name in ('certifi', 'pip._vendor.certifi'):
        try:
            module = __import__(name, fromlist=['where'])
            return ssl.create_default_context(cafile=module.where())
        except (ImportError, OSError, AttributeError):
            continue
    return ssl.create_default_context()


_CONTEXT = None


def request(method, url, key_id, secret, body=b'', headers=None):
    payload = hashlib.sha256(body).hexdigest()
    signed = sign(method, url, headers or {}, payload, key_id, secret, datetime.now(timezone.utc))
    signed.pop('host')
    req = urllib.request.Request(url, data=body if method in ('PUT', 'POST') else None, method=method, headers=signed)
    try:
        global _CONTEXT
        _CONTEXT = _CONTEXT or tls_context()
        with urllib.request.urlopen(req, timeout=120, context=_CONTEXT) as answer:
            return answer.read()
    except urllib.error.HTTPError as exc:
        text = exc.read().decode('utf-8', 'replace')
        code = ET.fromstring(text).findtext('Code') if text.startswith('<') else ''
        raise SystemExit(f'{method} {url}: {exc.code} {code or text[:200]}') from None
    except urllib.error.URLError as exc:
        raise SystemExit(f'{method} {url}: нет соединения — {exc.reason}') from None


def remote(bucket, key_id, secret):
    """{key: md5} of the objects of the bucket (ListObjectsV2, pages of 1000)."""
    found, token = {}, None
    ns = '{http://s3.amazonaws.com/doc/2006-03-01/}'
    while True:
        query = 'list-type=2&max-keys=1000' + ('&continuation-token=' + urllib.parse.quote(token, safe='') if token else '')
        root = ET.fromstring(request('GET', object_url(bucket, query=query), key_id, secret))
        for item in root.iter(ns + 'Contents'):
            found[item.findtext(ns + 'Key')] = (item.findtext(ns + 'ETag') or '').strip('"')
        token = root.findtext(ns + 'NextContinuationToken')
        if not token:
            return found


def local(folder):
    """{key: path} of the files of the built site (the files of other hostings left out)."""
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): p for p in sorted(folder.rglob('*'))
            if p.is_file() and p.name not in SKIP and not any(part.startswith('.') for part in p.relative_to(folder).parts)}


def plan(files, objects):
    """(to send, unchanged, only in the bucket): the files whose MD5 differs from the ETag of the object are sent."""
    send, same = [], []
    for key, path in files.items():
        (same if objects.get(key) == hashlib.md5(path.read_bytes()).hexdigest() else send).append(key)
    return send, same, sorted(set(objects) - set(files))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('folder', help='the folder of the built site (tools/build_atlas_site.py --out …)')
    parser.add_argument('--bucket', default=BUCKET)
    parser.add_argument('--delete', action='store_true', help='delete the objects the folder no longer has')
    parser.add_argument('--dry-run', action='store_true', help='only say what would be sent')
    args = parser.parse_args(argv)
    key_id, secret = os.environ.get('AWS_ACCESS_KEY_ID', ''), os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    if not key_id or not secret:
        sys.exit('Нужен статический ключ сервисного аккаунта: export AWS_ACCESS_KEY_ID=… AWS_SECRET_ACCESS_KEY=…')
    if not (key_id + secret).isascii() or ' ' in key_id + secret:  # the words of the example were taken
        sys.exit('В AWS_ACCESS_KEY_ID или AWS_SECRET_ACCESS_KEY не ключ: в нём русские буквы или пробелы. Вставьте '
                 'значения статического ключа из консоли Яндекса (идентификатор начинается на YCAJ).')
    files = local(args.folder)
    if 'index.html' not in files:
        sys.exit(f'{args.folder}: нет index.html — это не папка собранного сайта')
    send, same, extra = plan(files, remote(args.bucket, key_id, secret))
    print(f'Файлов {len(files)}: отправить {len(send)}, без изменений {len(same)}; лишних в бакете {len(extra)}.')
    if args.dry_run:
        return 0
    for n, key in enumerate(send, 1):
        body = files[key].read_bytes()
        request('PUT', object_url(args.bucket, key), key_id, secret, body,
                {'Content-Type': content_type(key), 'Cache-Control': cache_control(key)})
        print(f'  [{n}/{len(send)}] {key}', flush=True)
    for key in extra:
        if args.delete:
            request('DELETE', object_url(args.bucket, key), key_id, secret)
            print('  удалён', key)
        else:
            print('  лишний (не удалён):', key)
    print(f'Готово: https://{args.bucket}/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
