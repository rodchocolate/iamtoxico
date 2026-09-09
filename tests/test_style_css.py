"""Regression: style.css's #grid rule must survive CSS parsing.

A comment containing a literal `*/` (e.g. glob text like `20260808_*/`)
terminates early and the trailing garbage swallows the next rule, so the
#grid rule silently disappears and drop/preview pages render display:block
instead of the 3-col grid. This parses style.css with tinycss2 (a real CSS
tokenizer) exactly as a browser would and asserts the rule is intact.
"""
import os
import re

import pytest
import tinycss2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_PATH = os.path.join(ROOT, 'style.css')


@pytest.fixture(scope='module')
def stylesheet():
    css = open(CSS_PATH, encoding='utf-8').read()
    return css, tinycss2.parse_stylesheet(css, skip_comments=True,
                                          skip_whitespace=True)


def _prelude(rule):
    return tinycss2.serialize(rule.prelude).strip()


def _decls(rule):
    out = {}
    for d in tinycss2.parse_declaration_list(rule.content):
        if d.type == 'declaration':
            out[d.lower_name] = tinycss2.serialize(d.value).strip()
    return out


def _find_rule(rules, selector):
    return [r for r in rules if r.type == 'qualified-rule'
            and _prelude(r) == selector]


def test_no_parse_errors(stylesheet):
    _, rules = stylesheet
    errors = [r for r in rules if r.type == 'error']
    assert not errors, f'style.css has parse errors: {errors}'


def test_grid_rule_survives_parsing(stylesheet):
    """Top-level #grid must parse out with display:grid, 3 desktop columns."""
    _, rules = stylesheet
    grid_rules = _find_rule(rules, '#grid')
    assert grid_rules, (
        '#grid rule missing after parsing style.css — a malformed comment '
        'is likely swallowing it (comments must not contain a literal */)')
    decls = _decls(grid_rules[0])
    assert decls.get('display') == 'grid', decls
    assert re.sub(r'\s', '', decls.get('grid-template-columns', '')) == \
        'repeat(3,1fr)', decls


def test_mobile_media_query_gives_two_columns(stylesheet):
    """The max-width:768px media block keeps its 2-col #grid override."""
    _, rules = stylesheet
    media = [r for r in rules if r.type == 'at-rule' and r.lower_at_keyword
             == 'media' and 'max-width' in tinycss2.serialize(r.prelude)]
    assert media, 'mobile @media block missing from style.css'
    found = False
    for block in media:
        inner = tinycss2.parse_rule_list(block.content)
        for rule in _find_rule(inner, '#grid'):
            decls = _decls(rule)
            if re.sub(r'\s', '', decls.get('grid-template-columns', '')) == \
                    'repeat(2,1fr)':
                found = True
    assert found, 'mobile #grid 2-col override missing or unparsable'


def test_comments_contain_no_embedded_terminator():
    """No comment body in style.css may contain text that reads as */ ."""
    css = open(CSS_PATH, encoding='utf-8').read()
    bad = []
    for m in re.finditer(r'/\*', css):
        end = css.find('*/', m.end())
        assert end != -1, 'unterminated comment in style.css'
        # after the true comment ends, the next few chars must not look like
        # leftover comment prose (heuristic: a second */ closely following
        # means the comment was cut early by an embedded */)
        tail = css[end + 2:end + 120]
        if '*/' in tail and '/*' not in tail.split('*/')[0]:
            bad.append(css[m.start():end + 2])
    assert not bad, f'comment(s) with embedded */ terminator: {bad}'
