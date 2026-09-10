// Real-browser recovery tests; local HTTP only, all external requests blocked.
// Run: node tests/cart_recovery.mjs [optional evidence directory]
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const evidence = process.argv[2];
const server = http.createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const file = path.resolve(root, '.' + pathname);
    if (!file.startsWith(root + path.sep)) throw new Error('outside root');
    res.setHeader('Content-Type', file.endsWith('.js') ? 'application/javascript' :
      file.endsWith('.html') ? 'text/html' : 'application/octet-stream');
    res.end(await fs.readFile(file));
  } catch { res.writeHead(404); res.end('not found'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const variants = JSON.parse(await fs.readFile(path.join(root, 'data/shopify_variants.json'))).products;
const pages = (await fs.readdir(path.join(root, 'product'))).filter(n => n.endsWith('.html')).sort();
const filename = pages.find(n => variants[n.slice(0, -5)]?.v.some(v => v.a));
assert.ok(filename, 'need a real product with an available variant');
const handle = filename.slice(0, -5);
const results = [];
let browser;
try {
  browser = await chromium.launch({headless: true});
  for (const mode of ['http', 'network', 'json', 'schema', 'missing', 'timeout']) {
    const context = await browser.newContext({viewport: {width: 390, height: 844}});
    let requests = 0;
    await context.route('**/*', async route => {
      const url = route.request().url();
      if (!url.startsWith(base)) return route.abort();
      if (url.endsWith('/data/shopify_variants.json')) {
        requests++;
        if (requests > 1) return route.fulfill({json: {products: {[handle]: variants[handle]}}});
        if (mode === 'http') return route.fulfill({status: 503, body: 'unavailable'});
        if (mode === 'network') return route.abort('failed');
        if (mode === 'json') return route.fulfill({contentType: 'application/json', body: '{broken'});
        if (mode === 'schema') return route.fulfill({json: {products: {[handle]: {t: 'broken', v: 'invalid'}}}});
        if (mode === 'missing') return route.fulfill({json: {products: {}}});
        if (mode === 'timeout') return; // intentionally unresolved until abort/teardown
      }
      return route.continue();
    });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${base}/product/${filename}`);
    const startingURL = page.url();
    await page.locator('a.buy').first().click();
    await page.locator('.txc-error').waitFor({timeout: 12000});
    assert.equal(page.url(), startingURL, `${mode}: must not navigate/reload`);
    assert.match(await page.locator('.txc-error').innerText(), /unable|could not|unavailable/i);
    assert.equal(await page.locator('.txc-fallback').getAttribute('href'),
      `https://shop.iamtoxico.com/products/${handle}`);
    if (evidence && mode === 'http') {
      await fs.mkdir(evidence, {recursive: true});
      await page.screenshot({path: path.join(evidence, 'cart-error-mobile-390x844.png')});
    }
    await page.getByRole('button', {name: 'retry', exact: true}).click();
    await page.locator('.txc-sizes button:not([disabled])').first().waitFor();
    assert.equal(requests, 2, `${mode}: retry must refetch`);
    await page.locator('.txc-sizes button:not([disabled])').first().click();
    await page.locator('.txc-drawer').waitFor();
    assert.equal(await page.locator('.txc-item').count(), 1);
    assert.deepEqual(errors, [], `${mode}: no uncaught browser errors`);
    results.push({mode, requests, recovered: true, checkout_clicked: false});
    await context.close();
  }
  const noJS = await browser.newContext({javaScriptEnabled: false});
  await noJS.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort());
  const page = await noJS.newPage();
  await page.goto(`${base}/product/${filename}`);
  assert.equal(await page.locator('a.buy').first().getAttribute('href'),
    `https://shop.iamtoxico.com/products/${handle}`, 'no-JS buy must have canonical destination');
  results.push({mode: 'no-javascript', canonical_fallback: true, checkout_clicked: false});
  await noJS.close();
  const report = JSON.stringify({product: filename, results}, null, 2) + '\n';
  if (evidence) await fs.writeFile(path.join(evidence, 'cart-browser.json'), report);
  console.log(report);
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
