"""tools/upload_site_yandex.py — the upload of the mirror of the site to Yandex Object Storage.

Oracle of the signature: the example of the documentation of Amazon S3, «Signature Calculations for the Authorization
Header» (GET /test.txt with Range bytes=0-9, 2013-05-24, us-east-1, the example key) — its signature
f0e8bdb8…bdb41."""

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))

import upload_site_yandex as up  # noqa: E402


def test_the_signature_of_the_example_of_amazon():
    headers = up.sign('GET', 'https://examplebucket.s3.amazonaws.com/test.txt', {'Range': 'bytes=0-9'},
                      hashlib.sha256(b'').hexdigest(), 'AKIAIOSFODNN7EXAMPLE',
                      'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY', datetime(2013, 5, 24, tzinfo=timezone.utc),
                      region='us-east-1')
    assert headers['authorization'] == (
        'AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request, '
        'SignedHeaders=host;range;x-amz-content-sha256;x-amz-date, '
        'Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41')


def test_the_types_and_the_caching():
    assert up.content_type('atlas/assets/pyodide-0.26.4/pyodide.asm.wasm') == 'application/wasm'
    assert up.content_type('index.html') == 'text/html; charset=utf-8'
    assert up.content_type('rail.js') == 'text/javascript; charset=utf-8'
    assert up.content_type('img/og.jpg') == 'image/jpeg'
    assert up.cache_control('sw.js') == up.cache_control('atlas/ru/index.html') == 'no-cache'
    assert up.cache_control('img/og.jpg').startswith('public')
    # a new rail.js was not seen after a publication — scripts and styles are asked anew too
    assert up.cache_control('rail.js') == up.cache_control('atlas/assets/css/site-page.css') == 'no-cache'
    assert up.cache_control('atlas/assets/pyodide-0.26.4/pyodide.asm.js').startswith('public')
    assert up.object_url('ru.azimuth-chem.com', 'atlas/ru/тема.html') == \
        'https://storage.yandexcloud.net/ru.azimuth-chem.com/atlas/ru/%D1%82%D0%B5%D0%BC%D0%B0.html'


def test_the_plan(tmp_path):
    (tmp_path / 'index.html').write_text('<p>1</p>', encoding='utf-8')
    (tmp_path / 'a').mkdir()
    (tmp_path / 'a' / 'b.js').write_text('x', encoding='utf-8')
    for name in ('_headers', '_redirects', '.nojekyll'):
        (tmp_path / name).write_text('', encoding='ascii')
    (tmp_path / '.pyodide').mkdir()
    (tmp_path / '.pyodide' / 'big.tar').write_bytes(b'0')
    files = up.local(tmp_path)
    assert sorted(files) == ['a/b.js', 'index.html']
    objects = {'index.html': hashlib.md5(b'<p>1</p>').hexdigest(), 'a/b.js': 'old', 'gone.html': 'x'}
    assert up.plan(files, objects) == (['a/b.js'], ['index.html'], ['gone.html'])


def test_a_context_of_certificates():
    import ssl

    assert isinstance(up.tls_context(), ssl.SSLContext)
