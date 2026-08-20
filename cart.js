/* iamtoxico on-site cart
 *
 * Keeps shoppers on the site until payment: intercepts clicks on Shopify
 * product links (a[href*="myshopify.com/products/..."]), opens an on-site
 * size picker, collects items in a cart drawer (localStorage), and checks
 * out via a single cart permalink straight to Shopify's payment page.
 *
 * Variant data comes from /data/shopify_variants.json (built by
 * scripts/sync_shopify_variants.py). If the data or a handle is missing the
 * click falls through to normal navigation, so buying never breaks.
 *
 * SHOP_BASE flips to https://shop.iamtoxico.com once that domain is primary.
 */
(function () {
  'use strict';

  var SHOP_BASE = 'https://shop.iamtoxico.com';
  var DATA_URL = '/data/shopify_variants.json';
  var STORE_KEY = 'toxico_cart_v1';
  var PRODUCT_RE = /(?:myshopify\.com|shop\.iamtoxico\.com)\/products\/([^/?#]+)/;
  var LOCAL_BUY_RE = /\/product\/([^/?#]+)\.html$/;

  var dataPromise = null;
  function loadData() {
    if (!dataPromise) {
      dataPromise = fetch(DATA_URL).then(function (r) {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      }).then(function (d) { return d.products || {}; });
    }
    return dataPromise;
  }

  /* ---------- cart state ---------- */

  function readCart() {
    try {
      var items = JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
      return Array.isArray(items) ? items : [];
    } catch (e) { return []; }
  }
  function writeCart(items) {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(items)); } catch (e) {}
    renderBadge(items);
  }
  function addItem(items, entry) {
    for (var i = 0; i < items.length; i++) {
      if (items[i].id === entry.id) { items[i].q += 1; return items; }
    }
    items.push(entry);
    return items;
  }
  function money(n) {
    var v = Math.round(n * 100) / 100;
    return '$' + (v % 1 === 0 ? String(v) : v.toFixed(2));
  }

  /* ---------- dom ---------- */

  var CSS =
    '.txc-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:9000}' +
    '.txc-panel{position:fixed;z-index:9001;background:#0b0b0b;color:#fff;' +
      'border:1px solid rgba(255,255,255,.15);font:inherit}' +
    '.txc-picker{left:50%;top:50%;transform:translate(-50%,-50%);border-radius:12px;' +
      'padding:20px;width:min(340px,calc(100vw - 40px))}' +
    '.txc-picker h3{margin:0 0 2px;font-size:1.05rem;font-weight:600}' +
    '.txc-picker .txc-price{color:#bfbfbf;margin:0 0 14px}' +
    '.txc-sizes{display:flex;flex-wrap:wrap;gap:8px}' +
    '.txc-sizes button{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.3);' +
      'border-radius:8px;padding:8px 14px;cursor:pointer;font:inherit}' +
    '.txc-sizes button:hover{border-color:#fff}' +
    '.txc-sizes button[disabled]{opacity:.35;cursor:default;text-decoration:line-through}' +
    '.txc-drawer{top:0;right:0;height:100%;width:min(360px,100vw);display:flex;' +
      'flex-direction:column;border-width:0 0 0 1px}' +
    '.txc-drawer header{display:flex;justify-content:space-between;align-items:center;' +
      'padding:16px 18px;border-bottom:1px solid rgba(255,255,255,.12)}' +
    '.txc-drawer header h3{margin:0;font-size:1rem;font-weight:600;letter-spacing:.06em}' +
    '.txc-items{flex:1;overflow-y:auto;padding:8px 18px}' +
    '.txc-item{display:flex;justify-content:space-between;align-items:center;gap:10px;' +
      'padding:10px 0;border-bottom:1px solid rgba(255,255,255,.08)}' +
    '.txc-item .txc-name{flex:1;min-width:0}' +
    '.txc-item .txc-name div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.txc-item .txc-sub{color:#bfbfbf;font-size:.85em}' +
    '.txc-qty{display:flex;align-items:center;gap:6px}' +
    '.txc-qty button,.txc-x{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.3);' +
      'border-radius:6px;width:24px;height:24px;line-height:1;cursor:pointer;font:inherit;padding:0}' +
    '.txc-x{border:none;color:#bfbfbf}' +
    '.txc-empty{color:#bfbfbf;padding:24px 0;text-align:center}' +
    '.txc-foot{padding:16px 18px;border-top:1px solid rgba(255,255,255,.12)}' +
    '.txc-total{display:flex;justify-content:space-between;margin-bottom:12px;color:#bfbfbf}' +
    '.txc-checkout{display:block;width:100%;background:#fff;color:#0b0b0b;border:none;' +
      'border-radius:8px;padding:12px;font:inherit;font-weight:600;letter-spacing:.06em;cursor:pointer}' +
    '.txc-close{background:transparent;border:none;color:#bfbfbf;font:inherit;font-size:1.2rem;' +
      'cursor:pointer;padding:0 2px}' +
    '.txc-fab{position:fixed;right:18px;bottom:18px;z-index:8999;background:#0b0b0b;color:#fff;' +
      'border:1px solid rgba(255,255,255,.3);border-radius:999px;padding:10px 16px;cursor:pointer;' +
      'font:inherit;letter-spacing:.06em}' +
    '.txc-fab[hidden]{display:none}';

  var styleEl = null, fab = null, overlay = null;

  function ensureBase() {
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.textContent = CSS;
      document.head.appendChild(styleEl);
    }
    if (!fab) {
      fab = document.createElement('button');
      fab.className = 'txc-fab';
      fab.type = 'button';
      fab.addEventListener('click', function () { openDrawer(); });
      document.body.appendChild(fab);
    }
    renderBadge(readCart());
  }

  function renderBadge(items) {
    if (!fab) return;
    var n = items.reduce(function (a, it) { return a + it.q; }, 0);
    fab.textContent = 'cart (' + n + ')';
    fab.hidden = n === 0;
  }

  function closeOverlay() {
    if (overlay) { overlay.remove(); overlay = null; }
    document.removeEventListener('keydown', onEsc);
  }
  function onEsc(e) { if (e.key === 'Escape') closeOverlay(); }

  function openOverlay(panelClass) {
    closeOverlay();
    overlay = document.createElement('div');
    var backdrop = document.createElement('div');
    backdrop.className = 'txc-backdrop';
    backdrop.addEventListener('click', closeOverlay);
    var panel = document.createElement('div');
    panel.className = 'txc-panel ' + panelClass;
    overlay.appendChild(backdrop);
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    document.addEventListener('keydown', onEsc);
    return panel;
  }

  /* ---------- size picker ---------- */

  function openPicker(handle, product) {
    var panel = openOverlay('txc-picker');
    var prices = product.v.map(function (v) { return parseFloat(v.p) || 0; });
    var price = prices.length ? Math.min.apply(null, prices) : 0;

    var h = document.createElement('h3');
    h.textContent = product.t.toLowerCase();
    var pr = document.createElement('p');
    pr.className = 'txc-price';
    pr.textContent = money(price);
    var sizes = document.createElement('div');
    sizes.className = 'txc-sizes';

    product.v.forEach(function (v) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = v.s || 'one size';
      if (!v.a) b.disabled = true;
      b.addEventListener('click', function () {
        writeCart(addItem(readCart(), {
          id: v.id, h: handle, t: product.t, s: v.s, p: parseFloat(v.p) || 0, q: 1
        }));
        openDrawer();
      });
      sizes.appendChild(b);
    });

    panel.appendChild(h);
    panel.appendChild(pr);
    panel.appendChild(sizes);
  }

  /* ---------- drawer ---------- */

  function openDrawer() {
    var panel = openOverlay('txc-drawer');
    var items = readCart();

    var head = document.createElement('header');
    var title = document.createElement('h3');
    title.textContent = 'cart';
    var close = document.createElement('button');
    close.className = 'txc-close';
    close.type = 'button';
    close.setAttribute('aria-label', 'close');
    close.textContent = '×';
    close.addEventListener('click', closeOverlay);
    head.appendChild(title);
    head.appendChild(close);
    panel.appendChild(head);

    var list = document.createElement('div');
    list.className = 'txc-items';
    panel.appendChild(list);

    if (!items.length) {
      var empty = document.createElement('div');
      empty.className = 'txc-empty';
      empty.textContent = 'your cart is empty';
      list.appendChild(empty);
      return;
    }

    items.forEach(function (it) {
      var row = document.createElement('div');
      row.className = 'txc-item';

      var name = document.createElement('div');
      name.className = 'txc-name';
      var t = document.createElement('div');
      t.textContent = it.t.toLowerCase();
      var sub = document.createElement('div');
      sub.className = 'txc-sub';
      sub.textContent = (it.s ? it.s + ' · ' : '') + money(it.p);
      name.appendChild(t);
      name.appendChild(sub);

      var qty = document.createElement('div');
      qty.className = 'txc-qty';
      var minus = document.createElement('button');
      minus.type = 'button'; minus.textContent = '−';
      var count = document.createElement('span');
      count.textContent = String(it.q);
      var plus = document.createElement('button');
      plus.type = 'button'; plus.textContent = '+';
      minus.addEventListener('click', function () { bump(it.id, -1); });
      plus.addEventListener('click', function () { bump(it.id, 1); });
      qty.appendChild(minus); qty.appendChild(count); qty.appendChild(plus);

      var x = document.createElement('button');
      x.className = 'txc-x';
      x.type = 'button';
      x.setAttribute('aria-label', 'remove');
      x.textContent = '×';
      x.addEventListener('click', function () { bump(it.id, -it.q); });

      row.appendChild(name);
      row.appendChild(qty);
      row.appendChild(x);
      list.appendChild(row);
    });

    var foot = document.createElement('div');
    foot.className = 'txc-foot';
    var total = document.createElement('div');
    total.className = 'txc-total';
    var tl = document.createElement('span');
    tl.textContent = 'subtotal';
    var tv = document.createElement('span');
    tv.textContent = money(items.reduce(function (a, it) { return a + it.p * it.q; }, 0));
    total.appendChild(tl);
    total.appendChild(tv);
    var go = document.createElement('button');
    go.className = 'txc-checkout';
    go.type = 'button';
    go.textContent = 'checkout';
    go.addEventListener('click', function () {
      var cart = readCart();
      if (!cart.length) return;
      var path = cart.map(function (it) { return it.id + ':' + it.q; }).join(',');
      window.location.href = SHOP_BASE + '/cart/' + path;
    });
    foot.appendChild(total);
    foot.appendChild(go);
    panel.appendChild(foot);
  }

  function bump(id, delta) {
    var items = readCart();
    for (var i = 0; i < items.length; i++) {
      if (items[i].id === id) {
        items[i].q += delta;
        if (items[i].q <= 0) items.splice(i, 1);
        break;
      }
    }
    writeCart(items);
    openDrawer();
  }

  /* ---------- link interception ---------- */

  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var m = PRODUCT_RE.exec(a.href);
    if (!m && a.classList.contains('buy')) m = LOCAL_BUY_RE.exec(a.pathname || a.href);
    if (!m) return;
    var handle = m[1];
    e.preventDefault();
    loadData().then(function (products) {
      var product = products[handle];
      if (product) openPicker(handle, product);
      else window.location.href = a.href;
    }).catch(function () {
      window.location.href = a.href;
    });
  }, true);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ensureBase);
  } else {
    ensureBase();
  }
}());
