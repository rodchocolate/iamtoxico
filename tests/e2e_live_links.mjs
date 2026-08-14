/* Live-site buy-flow test: shoppers stay on iamtoxico.com until checkout.
 *
 * From the landing page, samples product rows (3 originals, 3 foolswise,
 * 6 scratch) and for each row's first product tile asserts:
 *   1. the tile link is same-origin (no myshopify, no raw image link)
 *   2. it resolves to an in-site /product/ page with title, price, buy
 *   3. clicking buy opens the on-site size picker (no navigation, no new tab)
 *   4. picking a size opens the cart drawer with a checkout button
 *
 * Run:  node tests/e2e_live_links.mjs   (needs npx playwright + chromium)
 */
import { chromium } from 'playwright';

const SITE = 'https://iamtoxico.com';
const failures = [];
const passes = [];

function classify(href) {
  if (href.includes('/designs/')) return 'originals';
  if (href.includes('foolswise')) return 'foolswise';
  if (href.includes('/scratch/')) return 'scratch';
  return null;
}

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(SITE, { waitUntil: 'domcontentloaded' });

// collect rows: label link -> first product tile in the following grid
const rows = await page.$$eval('.row-label', labels =>
  labels.map(label => {
    const a = label.querySelector('a');
    const grid = label.nextElementSibling;
    if (!a || !grid || !grid.classList.contains('grid')) return null;
    const tiles = [...grid.querySelectorAll('a.card, a.img-link')].map(t => ({
      href: t.getAttribute('href'),
      title: (t.querySelector('.title') || {}).textContent || '',
      meta: (t.querySelector('.meta') || {}).textContent || '',
    }));
    const product = tiles.find(t => t.meta.includes('$') || t.href.includes('/product/'));
    return { label: a.textContent.trim(), labelHref: a.getAttribute('href'), product, tiles };
  }).filter(Boolean)
);

const wanted = { originals: 3, foolswise: 3, scratch: 6 };
const picked = [];
for (const row of rows) {
  const kind = classify(row.labelHref || '');
  if (kind && wanted[kind] > 0 && row.product) {
    wanted[kind]--;
    picked.push({ ...row, kind });
  }
}
const short = Object.entries(wanted).filter(([, n]) => n > 0);
if (short.length) failures.push(`could not find enough rows: ${JSON.stringify(Object.fromEntries(short))}`);

// landing must have zero external product links at all
const external = await page.$$eval('a[href]', as =>
  as.map(a => a.href).filter(h => /myshopify\.com/.test(h)));
if (external.length) failures.push(`landing has ${external.length} myshopify links: ${external[0]}`);
else passes.push('landing: no external product links');

for (const row of picked) {
  const name = `${row.kind}/${row.label.replace(/\s*→\s*$/, '')}`;
  const href = row.product.href;
  try {
    const resolved = new URL(href, SITE + '/');
    if (/myshopify\.com/.test(resolved.hostname)) throw new Error(`tile links off-site: ${href}`);
    if (!resolved.hostname.endsWith('iamtoxico.com')) throw new Error(`tile links off-site: ${href}`);
    if (/\.(jpe?g|png|webp)(\?|$)/i.test(resolved.pathname)) throw new Error(`tile links a raw image: ${href}`);
    if (!resolved.pathname.includes('/product/')) throw new Error(`tile is not an in-site product page: ${href}`);

    const p = await browser.newPage();
    const resp = await p.goto(new URL(href, SITE).toString(), { waitUntil: 'domcontentloaded' });
    if (!resp.ok()) throw new Error(`product page HTTP ${resp.status()}`);
    if (!new URL(p.url()).hostname.endsWith('iamtoxico.com')) throw new Error(`left the site: ${p.url()}`);
    await p.waitForSelector('.pinfo h2', { timeout: 10000 });
    await p.waitForSelector('.pinfo .price', { timeout: 5000 });

    // buy -> on-site picker, not navigation, not a popup
    let popup = null;
    p.on('popup', pg => { popup = pg; });
    await p.click('a.buy');
    await p.waitForSelector('.txc-picker', { timeout: 10000 });
    if (popup) throw new Error('buy opened a new tab instead of the picker');
    if (!new URL(p.url()).hostname.endsWith('iamtoxico.com')) throw new Error(`buy navigated off-site: ${p.url()}`);

    // size -> cart drawer with checkout
    await p.click('.txc-sizes button:not([disabled])');
    await p.waitForSelector('.txc-drawer .txc-checkout', { timeout: 10000 });

    passes.push(`${name}: tile -> ${href} -> picker -> cart OK`);
    await p.close();
  } catch (e) {
    failures.push(`${name}: ${e.message}`);
  }
}

await browser.close();

for (const m of passes) console.log('PASS', m);
for (const m of failures) console.log('FAIL', m);
console.log(`\n${passes.length} passed, ${failures.length} failed`);
process.exit(failures.length ? 1 : 0);
