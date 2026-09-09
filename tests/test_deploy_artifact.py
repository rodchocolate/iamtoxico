"""Deploy-artifact coverage: every foolswise family page linked from the
homepage must survive the deploy-godaddy.yml exclusion filter, while the raw
staging images at foolswise/ top level must stay excluded.

The exclusion expressions are parsed straight out of the workflow file (the
same `-x '<regex>'` patterns handed to lftp mirror), so this test cannot
drift from the deploy config.
"""
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(ROOT, '.github', 'workflows', 'deploy-godaddy.yml')

# The 29 foolswise families the homepage links to. Identity matters: a rename
# or a dropped family must fail loudly here, not just shift a count.
EXPECTED_FAMILIES = {
    'aspen', 'base', 'birthday', 'botanical', 'candlelight', 'casino',
    'champagne', 'extra', 'fall', 'hollywood', 'ibiza', 'kauai', 'miami',
    'nightclub', 'oaxaca', 'oregon', 'racetrack', 'robben-island', 'sedona',
    'ski', 'snowbird', 'snowboard', 'spring', 'srt8', 'stripclub', 'summer',
    'vermentino', 'whistler', 'winter',
}


def load_exclusion_patterns():
    """Parse the lftp -x '<regex>' exclusion expressions from the workflow."""
    text = open(WORKFLOW, encoding='utf-8').read()
    m = re.search(r'EXCLUDES="(.*)"', text)
    assert m, 'EXCLUDES line not found in deploy-godaddy.yml'
    patterns = re.findall(r"-x '([^']+)'", m.group(1))
    assert patterns, 'no -x exclusion patterns parsed from EXCLUDES'
    return patterns


def repo_files():
    """Git-tracked files = what actions/checkout gives the deploy job."""
    out = subprocess.run(
        ['git', 'ls-files', '-z'], cwd=ROOT, check=True,
        capture_output=True).stdout
    return [f.decode() for f in out.split(b'\0') if f]


def simulate_artifact():
    """Apply the workflow's exclusion regexes the way lftp mirror does:
    unanchored regex search against the path relative to the mirror root."""
    patterns = [re.compile(p) for p in load_exclusion_patterns()]
    artifact = set()
    for path in repo_files():
        if any(p.search(path) for p in patterns):
            continue
        artifact.add(path)
    return artifact


@pytest.fixture(scope='module')
def artifact():
    return simulate_artifact()


def homepage_family_slugs():
    html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    return set(re.findall(r'href="/foolswise/([a-z0-9-]+)/"', html))


def test_homepage_links_expected_families():
    slugs = homepage_family_slugs()
    assert slugs == EXPECTED_FAMILIES, (
        f'homepage foolswise families changed: '
        f'missing={sorted(EXPECTED_FAMILIES - slugs)} '
        f'extra={sorted(slugs - EXPECTED_FAMILIES)}')


def test_family_pages_ship_in_artifact(artifact):
    missing = sorted(
        slug for slug in homepage_family_slugs()
        if f'foolswise/{slug}/index.html' not in artifact)
    assert not missing, (
        f'{len(missing)} homepage-linked foolswise family pages are '
        f'excluded from the deploy artifact: {missing}')


def test_family_page_local_assets_ship(artifact):
    """Every root-relative asset referenced by a family page must deploy."""
    missing = []
    for slug in sorted(homepage_family_slugs()):
        page = os.path.join(ROOT, 'foolswise', slug, 'index.html')
        if not os.path.isfile(page):
            missing.append(f'{slug}: page missing from repo')
            continue
        html = open(page, encoding='utf-8').read()
        for ref in re.findall(r'(?:src|href)="(/[^"]+)"', html):
            path = ref.lstrip('/').split('?')[0].split('#')[0]
            if not path or path.endswith('/'):
                continue
            if os.path.isfile(os.path.join(ROOT, path)) and path not in artifact:
                missing.append(f'{slug}: {path}')
    assert not missing, f'family-page assets excluded from artifact: {missing}'


def test_staging_images_do_not_ship(artifact):
    """Raw staging PNGs and the pages map at foolswise/ top level stay private.

    NOTE: this (and the other `artifact`-fixture tests above) are the fast
    regex *simulation* of lftp's exclusion matching. They remain as a quick
    secondary check; the authoritative artifact tests below run the real
    lftp binary with the exact EXCLUDES from the workflow.
    """
    leaked = sorted(
        f for f in artifact
        if re.match(r'foolswise/[^/]+$', f))
    assert not leaked, f'foolswise top-level staging files would deploy: {leaked}'


# ---------------------------------------------------------------------------
# Authoritative artifact tests: run the REAL lftp publisher (file: protocol,
# local-to-local mirror) with the exact EXCLUDES parsed from
# .github/workflows/deploy-godaddy.yml, then inspect what actually landed.
# The regex tests above stay as a fast secondary check; these are the truth.
# ---------------------------------------------------------------------------

LFTP = shutil.which('lftp') or (
    '/opt/homebrew/bin/lftp' if os.path.exists('/opt/homebrew/bin/lftp') else None)


def build_lftp_artifact(dest):
    """Mirror the checkout into `dest` with real lftp + workflow EXCLUDES.

    Returns (log_text, relative_file_set).
    """
    patterns = load_exclusion_patterns()
    excludes = ' '.join("-x '%s'" % p for p in patterns)
    script = (
        'set xfer:log no; '
        'open file://localhost/; '
        'mirror --verbose %s %s %s; ' % (excludes, ROOT, dest) +
        'exit'
    )
    proc = subprocess.run(
        [LFTP, '-c', script], capture_output=True, text=True, timeout=1800)
    assert proc.returncode == 0, (
        f'lftp mirror failed (rc={proc.returncode}):\n'
        f'{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}')
    files = set()
    for dirpath, _dirnames, filenames in os.walk(dest):
        for fn in filenames:
            files.add(os.path.relpath(os.path.join(dirpath, fn), dest))
    return proc.stdout + proc.stderr, files


@pytest.fixture(scope='module')
def lftp_artifact(tmp_path_factory):
    if not LFTP:
        pytest.skip('lftp binary not found (looked on PATH and at '
                    '/opt/homebrew/bin/lftp) — cannot run the real-publisher '
                    'artifact test; the regex simulation above still ran')
    dest = tmp_path_factory.mktemp('lftp-artifact')
    _log, files = build_lftp_artifact(str(dest))
    return files


def test_lftp_family_pages_ship(lftp_artifact):
    """All 29 homepage-linked foolswise family pages land in the real artifact."""
    slugs = homepage_family_slugs()
    assert slugs == EXPECTED_FAMILIES
    missing = sorted(
        slug for slug in slugs
        if f'foolswise/{slug}/index.html' not in lftp_artifact)
    assert not missing, (
        f'{len(missing)} family pages missing from real lftp artifact: {missing}')


def test_lftp_no_foolswise_staging_files(lftp_artifact):
    """No foolswise top-level staging content (PNGs, _pages_map.json) deploys."""
    leaked = sorted(
        f for f in lftp_artifact if re.match(r'foolswise/[^/]+$', f))
    assert not leaked, f'foolswise staging files leaked into artifact: {leaked}'


def test_lftp_no_private_content_anywhere(lftp_artifact):
    """No non-public content anywhere in the real artifact."""
    bad_ext = ('.py', '.log', '.env', '.db')
    bad_dirs = ('tests/', 'scripts/', 'docs/', 'branding/', 'shopify-app/')
    leaked = sorted(
        f for f in lftp_artifact
        if f.endswith(bad_ext) or f.startswith(bad_dirs)
        or any(('/' + d) in ('/' + f) for d in bad_dirs))
    assert not leaked, f'private content leaked into real artifact: {leaked[:40]}'


def test_lftp_public_pages_present(lftp_artifact):
    """The storefront itself ships: homepage plus the product pages."""
    assert 'index.html' in lftp_artifact, 'index.html missing from artifact'
    products = [f for f in lftp_artifact
                if f.startswith('product/') and f.endswith('.html')]
    assert len(products) > 400, (
        f'expected the product catalog in the artifact, found {len(products)}')
