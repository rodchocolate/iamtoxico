"""Deploy-artifact coverage: every foolswise family page linked from the
homepage must survive the deploy-godaddy.yml exclusion filter, while the raw
staging images at foolswise/ top level must stay excluded.

The exclusion expressions are parsed straight out of the workflow file (the
same `-x '<regex>'` patterns handed to lftp mirror), so this test cannot
drift from the deploy config.
"""
import os
import re
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
    """Raw staging PNGs and the pages map at foolswise/ top level stay private."""
    leaked = sorted(
        f for f in artifact
        if re.match(r'foolswise/[^/]+$', f))
    assert not leaked, f'foolswise top-level staging files would deploy: {leaked}'
