<?php
// doubled.life — gated landing. Password (no username) -> 4-digit code emailed
// to Jason -> 15-min-idle session -> subject index + search. Subject pages under
// /s/ are open but unlisted; this landing is the only index of them.
// config.php is injected at deploy time from GitHub Actions secrets.

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
    if (isset($_POST['password'])) {
        if (hash_equals($config['pass_sha256'], hash('sha256', $_POST['password']))) {
            $code = strval(random_int(1000, 9999));
            save_state('code_' . session_id(),
                ['h' => hash('sha256', $code), 'exp' => time() + 600, 'tries' => 0]);
            @mail($config['email'], 'doubled.life code', "Access code: $code\n(expires in 10 minutes)",
                  "From: gate@doubled.life\r\n");
            $_SESSION['stage'] = 'code';
            $rl = ['fails' => 0, 'until' => 0]; save_state($rl_key, $rl);
        } else {
            $rl['fails']++;
            if ($rl['fails'] >= 5) { $rl['until'] = time() + 900; $rl['fails'] = 0; }
            save_state($rl_key, $rl);
            $msg = 'no';
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
$stage = $authed ? 'in' : (($_SESSION['stage'] ?? '') === 'code' ? 'code' : 'password');
$subjects = $authed ? ((@include __DIR__ . '/subjects.php') ?: []) : [];
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
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Space Grotesk', sans-serif; background: #0b0b0b; color: #fff; min-height: 100vh; }
  .gate { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem; }
  .gate h1 { font-size: 2rem; font-weight: 600; letter-spacing: .04em; text-transform: lowercase; }
  .gate form { display: flex; gap: .6rem; }
  .gate input { background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.2); color: #fff;
    font-family: inherit; font-size: 1rem; padding: .6em 1em; border-radius: 8px; width: 14rem; }
  .gate button { background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.25); color: #fff;
    font-family: inherit; font-size: 1rem; padding: .6em 1.2em; border-radius: 8px; cursor: pointer; }
  .gate .m { opacity: .5; font-size: .85rem; min-height: 1.2em; }
  header { padding: 1.5rem 2rem; max-width: 1280px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; }
  header h1 { font-size: 2rem; font-weight: 600; letter-spacing: .04em; text-transform: lowercase; }
  header input { background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.2); color: #fff;
    font-family: inherit; font-size: .95rem; padding: .5em 1em; border-radius: 8px; width: 16rem; }
  main { padding: 1rem 2rem 4rem; max-width: 1280px; margin: 0 auto; }
  .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.4rem; }
  .card { background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1); border-radius: 12px;
    overflow: hidden; transition: transform .25s, border-color .25s; }
  .card:hover { transform: translateY(-4px); border-color: rgba(255,255,255,.25); }
  .card a { display: block; color: inherit; text-decoration: none; padding: 1.1rem 1.2rem; }
  .card .kind { font-size: .7rem; opacity: .5; text-transform: uppercase; letter-spacing: .1em; }
  .card .name { font-size: 1.1rem; font-weight: 600; margin: .2rem 0 .4rem; }
  .card .lede { font-size: .85rem; opacity: .7; line-height: 1.45; }
  @media (max-width: 768px) { .cards { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<?php if ($stage === 'password'): ?>
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
  <div class="m"><?= htmlspecialchars($msg ?: 'code sent') ?></div>
</div>
<?php else: ?>
<header>
  <h1>doubled.life</h1>
  <input type="search" id="q" placeholder="search">
</header>
<main>
  <div class="cards" id="cards">
  <?php foreach ($subjects as $s): ?>
    <div class="card" data-t="<?= htmlspecialchars(strtolower($s['name'] . ' ' . $s['kind'] . ' ' . $s['lede'])) ?>">
      <a href="<?= htmlspecialchars($s['url']) ?>">
        <div class="kind"><?= htmlspecialchars($s['kind']) ?></div>
        <div class="name"><?= htmlspecialchars($s['name']) ?></div>
        <div class="lede"><?= htmlspecialchars($s['lede']) ?></div>
      </a>
    </div>
  <?php endforeach; ?>
  </div>
</main>
<script>
document.getElementById('q').addEventListener('input', e => {
  const q = e.target.value.toLowerCase();
  document.querySelectorAll('#cards .card').forEach(c => {
    c.style.display = c.dataset.t.includes(q) ? '' : 'none';
  });
});
</script>
<?php endif; ?>
</body>
</html>
