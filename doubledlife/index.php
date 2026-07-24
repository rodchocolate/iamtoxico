<?php
// doubled.life — gated landing. Animated landing (cratetalk background) ->
// proceed -> password -> correct password emails a 4-digit code to Jason ->
// code entry -> 15-min-idle session -> subject index + search. The password
// gates the code SEND so strangers can't flood Jason's phone/inbox. Subject
// pages under /s/ are open but unlisted; this landing is the only index of
// them. config.php is injected at deploy time from GitHub Actions secrets.

$config = @include __DIR__ . '/config.php';
if (!$config) { http_response_code(503); exit('not configured'); }

$STATE = __DIR__ . '/../doubled_state';
if (!is_dir($STATE)) { @mkdir($STATE, 0700, true); }

// Session-only cookie + 15-min idle expiry: re-auth roughly every pocket/lock
// cycle on mobile, per Jason's preference. No persistent sessions.
session_set_cookie_params(['lifetime' => 0, 'httponly' => true, 'samesite' => 'Lax']);
ini_set('session.gc_maxlifetime', '3600');
session_start();
if (($_SESSION['auth'] ?? false) === true) {
    if (time() - ($_SESSION['last'] ?? 0) > 900) {
        session_unset();
    } else {
        $_SESSION['last'] = time();
    }
}

function state_path($name) { global $STATE; return $STATE . '/' . $name . '.json'; }
function load_state($name) { $p = state_path($name); return is_file($p) ? json_decode(file_get_contents($p), true) : null; }
function save_state($name, $d) { file_put_contents(state_path($name), json_encode($d), LOCK_EX); }

$ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
$rl_key = 'rl_' . md5($ip);
$rl = load_state($rl_key) ?: ['fails' => 0, 'until' => 0];
$locked = time() < ($rl['until'] ?? 0);
$msg = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST' && !$locked) {
    if (isset($_POST['proceed'])) {
        $_SESSION['stage'] = 'password';
    } elseif (isset($_POST['password']) && ($_SESSION['stage'] ?? '') === 'password') {
        // The password gates the code SEND — a wrong password never texts/emails.
        if (hash_equals($config['pass_sha256'], hash('sha256', $_POST['password']))) {
            $code = strval(random_int(1000, 9999));
            save_state('code_' . session_id(),
                ['h' => hash('sha256', $code), 'exp' => time() + 600, 'tries' => 0]);
            // Queue for the Studio poller (reliable Gmail SMTP + iMessage);
            // GoDaddy mail() is too unreliable to deliver codes.
            $pend = $STATE . '/pending';
            if (!is_dir($pend)) { @mkdir($pend, 0700, true); }
            file_put_contents($pend . '/' . session_id() . '.json',
                json_encode(['code' => $code, 'ts' => time()]), LOCK_EX);
            $_SESSION['stage'] = 'code';
            $_SESSION['last_send'] = time();
            $rl = ['fails' => 0, 'until' => 0]; save_state($rl_key, $rl);
        } else {
            $rl['fails']++;
            if ($rl['fails'] >= 5) { $rl['until'] = time() + 900; $rl['fails'] = 0; }
            save_state($rl_key, $rl);
            $msg = 'no';
        }
    } elseif (isset($_POST['resend']) && ($_SESSION['stage'] ?? '') === 'code') {
        // Resend: throttle to once per 15s so the button can't be spammed.
        if (time() - ($_SESSION['last_send'] ?? 0) >= 15) {
            $code = strval(random_int(1000, 9999));
            save_state('code_' . session_id(),
                ['h' => hash('sha256', $code), 'exp' => time() + 600, 'tries' => 0]);
            $pend = $STATE . '/pending';
            if (!is_dir($pend)) { @mkdir($pend, 0700, true); }
            file_put_contents($pend . '/' . session_id() . '.json',
                json_encode(['code' => $code, 'ts' => time()]), LOCK_EX);
            $_SESSION['last_send'] = time();
            $msg = 'resent';
        } else {
            $msg = 'wait a moment';
        }
    } elseif (isset($_POST['code']) && ($_SESSION['stage'] ?? '') === 'code') {
        $c = load_state('code_' . session_id());
        if ($c && time() < $c['exp'] && $c['tries'] < 5) {
            if (hash_equals($c['h'], hash('sha256', trim($_POST['code'])))) {
                $_SESSION['auth'] = true;
                $_SESSION['last'] = time();
                unset($_SESSION['stage']);
                @unlink(state_path('code_' . session_id()));
            } else {
                $c['tries']++; save_state('code_' . session_id(), $c);
                $msg = 'no';
            }
        } else {
            unset($_SESSION['stage']);
            $msg = 'expired — start over';
        }
    }
}

$authed = ($_SESSION['auth'] ?? false) === true;
$stage = 'landing';
if ($authed) { $stage = 'in'; }
elseif (($_SESSION['stage'] ?? '') === 'code') { $stage = 'code'; }
elseif (($_SESSION['stage'] ?? '') === 'password') { $stage = 'password'; }
$subjects = $authed ? ((@include __DIR__ . '/subjects.php') ?: []) : [];

// Notes tab: capture a planning note, queued for the Studio poller to record
// into Hermes alongside the research corpus.
$note_ok = false;
if ($authed && $_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['note'])) {
    $n = trim($_POST['note']);
    if ($n !== '') {
        $nd = $STATE . '/notes';
        if (!is_dir($nd)) { @mkdir($nd, 0700, true); }
        file_put_contents($nd . '/' . time() . '-' . bin2hex(random_bytes(3)) . '.json',
            json_encode(['note' => $n, 'ts' => time()]), LOCK_EX);
        $note_ok = true;
    }
}
$videos = array_values(array_filter($subjects, fn($s) => ($s['kind'] ?? '') === 'video'));
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex,nofollow">
<title>doubled.life</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&display=swap');
  :root {
    --bg: #26547c;            /* dusk blue — background */
    --text: #06d6a0;          /* emerald — main text */
    --porcelain: #fffcf9;     /* porcelain — detail */
    --line: rgba(255,252,249,.24);   /* porcelain borders */
    --panel: rgba(255,252,249,.06);
    --link: #ef476f;          /* bubblegum pink — link */
    --visited: #ffd166;       /* golden pollen — clicked */
    --hover: #fffcf9;         /* porcelain — hover highlight */
  }
  a { color: var(--link); }
  a:visited { color: var(--visited); }
  a:hover { color: var(--hover); }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Space Grotesk', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
  .gate { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem; }
  .gate.landing { background: var(--bg) url('landing.webp') center center / cover no-repeat; }
  .gate.landing h1, .gate.landing .m { text-shadow: 0 2px 12px rgba(0,0,0,.8); }
  .gate.landing button { background: rgba(0,0,0,.55); backdrop-filter: blur(2px); }
  .gate h1 { font-size: 2rem; font-weight: 600; letter-spacing: .04em; text-transform: lowercase; }
  .gate form { display: flex; gap: .6rem; }
  .gate input { background: var(--panel); border: 1px solid var(--line); color: #fff;
    font-family: inherit; font-size: 1rem; padding: .6em 1em; border-radius: 8px; width: 14rem; }
  .gate button { background: var(--line); border: 1px solid var(--line); color: #fff;
    font-family: inherit; font-size: 1rem; padding: .6em 1.2em; border-radius: 8px; cursor: pointer; }
  .gate .m { opacity: .5; font-size: .85rem; min-height: 1.2em; }
  header { padding: 1.5rem 2rem; max-width: 1280px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; }
  header h1 { font-size: 2rem; font-weight: 600; letter-spacing: .04em; text-transform: lowercase; }
  header input { background: var(--panel); border: 1px solid var(--line); color: #fff;
    font-family: inherit; font-size: .95rem; padding: .5em 1em; border-radius: 8px; width: 16rem; }
  main { padding: 1rem 2rem 4rem; max-width: 1280px; margin: 0 auto; }
  .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.4rem; }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
    overflow: hidden; transition: transform .25s, border-color .25s; }
  .card:hover { transform: translateY(-4px); border-color: var(--line); }
  .card a { display: block; color: var(--text); text-decoration: none; padding: 1.1rem 1.2rem; }
  .card .kind { font-size: .7rem; opacity: .5; text-transform: uppercase; letter-spacing: .1em; }
  .card .name { font-size: 1.1rem; font-weight: 600; margin: .2rem 0 .4rem; }
  .card .lede { font-size: .85rem; opacity: .7; line-height: 1.45; }
  .tabs { display: flex; gap: .3rem; max-width: 1280px; margin: 0 auto; padding: 0 2rem; }
  .tabs button { background: var(--panel); border: 1px solid var(--line); border-bottom: none;
    color: #fff; font-family: inherit; font-size: .8rem; letter-spacing: .06em; text-transform: lowercase;
    padding: .55em 1.3em; border-radius: 8px 8px 0 0; cursor: pointer; opacity: .55; }
  .tabs button.active { opacity: 1; background: var(--line); }
  .panel { display: none; }
  .panel.active { display: block; }
  .vgrid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.4rem; }
  .vtile { color: var(--text); position: relative; border-radius: 12px; overflow: hidden; border: 1px solid var(--line);
    aspect-ratio: 1; background: #1a1a1a; display: block; text-decoration: none; }
  .vtile img { width: 100%; height: 100%; object-fit: cover; transition: transform .3s; }
  .vtile:hover img { transform: scale(1.05); }
  .vtile .cap { position: absolute; inset: auto 0 0 0; padding: .8rem .9rem; color: #fff;
    font-size: .82rem; font-weight: 600; background: linear-gradient(transparent, rgba(0,0,0,.85)); }
  .qcard .st { font-size: .68rem; text-transform: uppercase; letter-spacing: .1em; margin-bottom: .3rem; }
  .qcard .st.run { color: #5fd08a; } .qcard .st.queued { color: #e0b64a; } .qcard .st.done { color: rgba(255,255,255,.4); }
  .notes textarea { width: 100%; min-height: 9rem; background: var(--panel); color: #fff;
    border: 1px solid var(--line); border-radius: 12px; padding: 1rem; font-family: inherit;
    font-size: .95rem; line-height: 1.5; resize: vertical; }
  .notes button { margin-top: .8rem; background: var(--line); border: 1px solid var(--line);
    color: #fff; font-family: inherit; font-size: .9rem; padding: .55em 1.4em; border-radius: 8px; cursor: pointer; }
  .notes .hint { font-size: .78rem; opacity: .5; margin-top: .6rem; }
  .empty { opacity: .4; font-size: .85rem; padding: 1rem 0; }
  .viewtoggle { display: flex; gap: 0; }
  .viewtoggle button { background: var(--panel); border: 1px solid var(--line);
    color: #fff; font-family: inherit; font-size: .72rem; text-transform: lowercase; letter-spacing: .06em;
    padding: .45em 1em; cursor: pointer; opacity: .5; }
  .viewtoggle button:first-child { border-radius: 8px 0 0 8px; }
  .viewtoggle button:last-child { border-radius: 0 8px 8px 0; border-left: none; }
  .viewtoggle button.active { opacity: 1; background: var(--panel); }
  .view { display: none; } .view.active { display: block; }
  .hero { color: var(--text); display: block; position: relative; max-width: 1280px; margin: 0 auto 1.8rem; border-radius: 16px;
    overflow: hidden; text-decoration: none; color: #fff; background: #161616; }
  .hero img { width: 100%; height: 420px; object-fit: cover; opacity: .82; display: block; }
  .hero .noimg { height: 300px; }
  .hero-body { position: absolute; inset: auto 0 0 0; padding: 2rem; background: linear-gradient(transparent, rgba(0,0,0,.92)); }
  .hero .kind { font-size: .7rem; text-transform: uppercase; letter-spacing: .12em; opacity: .7; }
  .hero-name { font-size: 2.4rem; font-weight: 600; margin: .2rem 0 .4rem; letter-spacing: .02em; }
  .hero-lede { font-size: 1rem; opacity: .82; max-width: 62ch; line-height: 1.5; }
  .river { max-width: 1280px; margin: 0 auto; display: grid; gap: 1.1rem; }
  .story { color: var(--text); display: grid; grid-template-columns: 190px 1fr; gap: 1.3rem; text-decoration: none; color: #fff;
    border-bottom: 1px solid var(--panel); padding-bottom: 1.1rem; align-items: start; }
  .story:hover .story-name { color: #9ecbff; }
  .story-thumb { width: 190px; height: 115px; border-radius: 10px; overflow: hidden; background: #1a1a1a;
    display: flex; align-items: center; justify-content: center; font-size: 2.4rem; font-weight: 600; color: rgba(255,255,255,.75); }
  .story-thumb img { width: 100%; height: 100%; object-fit: cover; }
  .story .meta { font-size: .68rem; text-transform: uppercase; letter-spacing: .1em; opacity: .5; }
  .story-name { font-size: 1.3rem; font-weight: 600; margin: .15rem 0 .35rem; }
  .story-lede { font-size: .88rem; opacity: .72; line-height: 1.5; }
  .card.qcard.link { cursor: pointer; }
  @media (max-width: 768px) { .cards, .vgrid { grid-template-columns: 1fr; } .tabs { flex-wrap: wrap; }
    .story { grid-template-columns: 110px 1fr; gap: .9rem; } .story-thumb { width: 110px; height: 80px; font-size: 1.6rem; }
    .hero-name { font-size: 1.6rem; } .hero img { height: 240px; } header { flex-wrap: wrap; gap: .6rem; } }
</style>
</head>
<body>
<?php if ($stage === 'landing'): ?>
<div class="gate landing">
  <h1>doubled.life</h1>
  <form method="post">
    <button type="submit" name="proceed" value="1">proceed</button>
  </form>
  <div class="m"></div>
</div>
<?php elseif ($stage === 'password'): ?>
<div class="gate">
  <h1>doubled.life</h1>
  <form method="post">
    <input type="password" name="password" autofocus autocomplete="current-password">
    <button type="submit">enter</button>
  </form>
  <div class="m"><?= $locked ? 'locked — try later' : htmlspecialchars($msg) ?></div>
</div>
<?php elseif ($stage === 'code'): ?>
<div class="gate">
  <h1>doubled.life</h1>
  <form method="post">
    <input type="text" name="code" inputmode="numeric" maxlength="4" placeholder="4-digit code" autofocus autocomplete="one-time-code">
    <button type="submit">confirm</button>
  </form>
  <form method="post" style="margin-top:.4rem">
    <button type="submit" name="resend" value="1" style="background:none;border:none;color:#fff;opacity:.55;text-decoration:underline;cursor:pointer;font-family:inherit;font-size:.8rem">resend code</button>
  </form>
  <div class="m"><?= htmlspecialchars($msg ?: 'code sent') ?></div>
</div>
<?php else:
  function dl_hue($s) { return crc32($s) % 360; }
  $hero = $subjects[0] ?? null;
  $rest = array_slice($subjects, 1);
?>
<header>
  <h1>doubled.life</h1>
  <div class="viewtoggle">
    <button class="active" data-view="espn">espn</button>
    <button data-view="napster">napster</button>
  </div>
  <input type="search" id="q" placeholder="search">
</header>

<!-- ESPN reading view (default) -->
<div class="view active" id="view-espn">
  <main>
  <?php if ($hero): ?>
    <a class="hero" href="<?= htmlspecialchars($hero['url']) ?>" target="_blank" rel="noopener"
       data-t="<?= htmlspecialchars(strtolower($hero['name'].' '.$hero['kind'].' '.$hero['lede'])) ?>">
      <?php if (!empty($hero['thumb'])): ?><img src="<?= htmlspecialchars($hero['thumb']) ?>" alt="">
      <?php else: ?><div class="noimg" style="background:hsl(<?= dl_hue($hero['name']) ?>,45%,20%)"></div><?php endif; ?>
      <div class="hero-body">
        <div class="kind"><?= htmlspecialchars($hero['kind']) ?></div>
        <div class="hero-name"><?= htmlspecialchars($hero['name']) ?></div>
        <div class="hero-lede"><?= htmlspecialchars($hero['lede']) ?></div>
      </div>
    </a>
    <div class="river">
    <?php foreach ($rest as $s): ?>
      <a class="story" href="<?= htmlspecialchars($s['url']) ?>" target="_blank" rel="noopener"
         data-t="<?= htmlspecialchars(strtolower($s['name'].' '.$s['kind'].' '.$s['lede'])) ?>">
        <div class="story-thumb" style="background:hsl(<?= dl_hue($s['name']) ?>,42%,18%)">
          <?php if (!empty($s['thumb'])): ?><img src="<?= htmlspecialchars($s['thumb']) ?>" alt="">
          <?php else: ?><?= htmlspecialchars(strtoupper(substr($s['name'],0,1))) ?><?php endif; ?>
        </div>
        <div class="story-body">
          <div class="meta"><?= htmlspecialchars($s['kind']) ?><?= $s['date'] ? ' · '.htmlspecialchars($s['date']) : '' ?></div>
          <div class="story-name"><?= htmlspecialchars($s['name']) ?></div>
          <div class="story-lede"><?= htmlspecialchars($s['lede']) ?></div>
        </div>
      </a>
    <?php endforeach; ?>
    </div>
  <?php else: ?><div class="empty">no research yet</div><?php endif; ?>
  </main>
</div>

<!-- Napster console view -->
<div class="view" id="view-napster">
<div class="tabs">
  <button class="active" data-tab="library">library</button>
  <button data-tab="video">video</button>
  <button data-tab="queue">queue</button>
  <button data-tab="notes">notes</button>
</div>
<main>
  <div class="panel active" id="library">
    <div class="cards" id="cards">
    <?php foreach ($subjects as $s): ?>
      <div class="card" data-t="<?= htmlspecialchars(strtolower($s['name'] . ' ' . $s['kind'] . ' ' . $s['lede'])) ?>">
        <a href="<?= htmlspecialchars($s['url']) ?>" target="_blank" rel="noopener">
          <div class="kind"><?= htmlspecialchars($s['kind']) ?></div>
          <div class="name"><?= htmlspecialchars($s['name']) ?></div>
          <div class="lede"><?= htmlspecialchars($s['lede']) ?></div>
        </a>
      </div>
    <?php endforeach; ?>
    </div>
  </div>

  <div class="panel" id="video">
    <?php if ($videos): ?>
    <div class="vgrid">
      <?php foreach ($videos as $v): ?>
      <a class="vtile" href="<?= htmlspecialchars($v['url']) ?>" target="_blank" rel="noopener"
         data-t="<?= htmlspecialchars(strtolower($v['name'] . ' ' . $v['lede'])) ?>">
        <?php if (!empty($v['thumb'])): ?><img src="<?= htmlspecialchars($v['thumb']) ?>" alt=""><?php endif; ?>
        <span class="cap"><?= htmlspecialchars($v['name']) ?></span>
      </a>
      <?php endforeach; ?>
    </div>
    <?php else: ?><div class="empty">no video research yet</div><?php endif; ?>
  </div>

  <div class="panel" id="queue">
    <div class="cards" id="qcards"><div class="empty">loading…</div></div>
  </div>

  <div class="panel" id="notes">
    <form method="post" class="notes">
      <textarea name="note" placeholder="a note for hermes — recorded for planning alongside the research corpus" autofocus></textarea>
      <button type="submit">send to hermes</button>
      <div class="hint"><?= $note_ok ? 'sent — hermes will log it' : 'goes into hermes planning; used when synthesizing across your research' ?></div>
    </form>
  </div>
</main>
</div>
<script>
const q = document.getElementById('q');
function esc(s){ return (s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function activeView(){ return document.querySelector('.view.active'); }
function filter() {
  const t = (q.value || '').toLowerCase();
  const scope = activeView().classList.contains('view') && activeView().id === 'view-napster'
    ? '.panel.active [data-t]' : '[data-t]';
  activeView().querySelectorAll(scope).forEach(c => {
    c.style.display = c.dataset.t.includes(t) ? '' : 'none';
  });
}
q.addEventListener('input', filter);

// view toggle (espn default), persisted
function setView(v) {
  document.querySelectorAll('.viewtoggle button').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  document.getElementById('view-espn').classList.toggle('active', v === 'espn');
  document.getElementById('view-napster').classList.toggle('active', v === 'napster');
  try { localStorage.setItem('dl_view', v); } catch (e) {}
  if (v === 'napster' && document.querySelector('.tabs .active')?.dataset.tab === 'queue') loadQueue();
  filter();
}
document.querySelectorAll('.viewtoggle button').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
try { const saved = localStorage.getItem('dl_view'); if (saved) setView(saved); } catch (e) {}

// napster tabs
document.querySelectorAll('.tabs button').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('.tabs button').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  document.getElementById(b.dataset.tab).classList.add('active');
  filter();
  if (b.dataset.tab === 'queue') loadQueue();
}));

function loadQueue() {
  fetch('gate_status.php').then(r => r.json()).then(d => {
    const el = document.getElementById('qcards');
    const jobs = (d && d.jobs) || [];
    if (!jobs.length) { el.innerHTML = '<div class="empty">nothing in the last 24 hours</div>'; return; }
    el.innerHTML = jobs.map(j => {
      const inner =
        '<div style="padding:1.1rem 1.2rem">' +
          '<div class="st ' + (j.status || 'done') + '">' + esc(j.status || '') +
            (j.url && j.status !== 'done' ? ' · view current' : '') + '</div>' +
          '<div class="name">' + esc(j.target || 'request') + '</div>' +
          '<div class="lede">' + esc(j.detail || '') + '</div>' +
        '</div>';
      const dt = 'data-t="' + esc((j.target || '').toLowerCase()) + '"';
      // a queue item behaves like a library card whenever a page exists — even
      // an in-progress update links to the existing page in the interim
      return j.url
        ? '<a class="card qcard link" href="' + esc(j.url) + '" target="_blank" rel="noopener" ' + dt + '>' + inner + '</a>'
        : '<div class="card qcard" ' + dt + '>' + inner + '</div>';
    }).join('');
    filter();
  }).catch(() => { document.getElementById('qcards').innerHTML = '<div class="empty">queue unavailable</div>'; });
}
</script>
<?php endif; ?>
</body>
</html>
