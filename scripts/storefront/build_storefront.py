#!/usr/bin/env python3
"""Retired one-shot storefront restructure script.

This originally ran once against a hardcoded runtime checkout
(/Users/melodiclabs/hermes-runtime/rooot/iamtoxico.com) using disposable /tmp
inputs (colormap.json, originals_data.json, avant_published.json,
scratch_src.json) and a sys.path hack into a session-local scratchpad. Those
inputs are gone, and the hardcoded path is outside this repo's control, so
re-running this script would either crash immediately or, worse, silently do
nothing useful while looking like it worked.

Supported replacement:
  - product/<handle>.html pages: scripts/build_product_pages.py --root <site-root>

There is no supported regenerator for originals.html or the landing
index.html — that content is hand-maintained. Do not try to reconstruct this
script's lost /tmp inputs to make it runnable again; that risks overwriting
deliberately hand-edited HTML with stale data.
"""
raise SystemExit(
    "scripts/storefront/build_storefront.py is retired: its /tmp inputs and "
    "scratchpad import no longer exist. Use "
    "`python3 scripts/build_product_pages.py --root <site-root>` for product "
    "pages; there is no supported regenerator for originals.html/index.html."
)
