// Local computed-style check for #grid on drop/preview pages (file://).
import { chromium } from 'playwright';
const ROOT = new URL('..', import.meta.url).pathname.replace(/\/$/, '');
const browser = await chromium.launch();
const failures = [];
async function check(pageFile, viewport, wantCols) {
  const p = await browser.newPage({ viewport });
  await p.goto(`file://${ROOT}/${pageFile}`, { waitUntil: 'load' });
  const r = await p.evaluate(() => {
    const g = document.getElementById('grid');
    const cs = getComputedStyle(g);
    return { display: cs.display, cols: cs.gridTemplateColumns.split(' ').length };
  });
  const label = `${pageFile} @${viewport.width}px`;
  if (r.display !== 'grid') failures.push(`${label}: display=${r.display}, want grid`);
  else if (r.cols !== wantCols) failures.push(`${label}: ${r.cols} cols, want ${wantCols}`);
  else console.log(`PASS ${label}: display=grid, ${r.cols} cols`);
  await p.close();
}
await check('20260808_1.html', { width: 1280, height: 900 }, 3);
await check('preview.html', { width: 1280, height: 900 }, 3);
await check('20260808_1.html', { width: 500, height: 800 }, 2);
await check('preview.html', { width: 500, height: 800 }, 2);
await browser.close();
for (const f of failures) console.log('FAIL', f);
process.exit(failures.length ? 1 : 0);
