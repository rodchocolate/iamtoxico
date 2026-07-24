<?php
// Queue status bridge. Studio poller POSTs the current jobs list (token-gated);
// the gated Queue tab GETs it (session-gated, since it lists research targets).
$config = @include __DIR__ . '/config.php';
$sf = __DIR__ . '/../doubled_state/status.json';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!$config || !hash_equals($config['poll_token'] ?? '', $_GET['token'] ?? '')) {
        http_response_code(403); exit('no');
    }
    $body = file_get_contents('php://input');
    if (json_decode($body) !== null) {
        if (!is_dir(dirname($sf))) { @mkdir(dirname($sf), 0700, true); }
        file_put_contents($sf, $body, LOCK_EX);
    }
    echo 'ok'; exit;
}

session_set_cookie_params(['lifetime' => 0, 'httponly' => true, 'samesite' => 'Lax']);
session_start();
if (($_SESSION['auth'] ?? false) !== true) { http_response_code(403); exit('no'); }
header('Content-Type: application/json');
echo is_file($sf) ? file_get_contents($sf) : '{"jobs":[]}';
