<?php
// Delivery queue drain for the Studio code poller. Returns + removes pending
// codes. Token-gated (shared secret); codes are one-time + 10-min TTL anyway.
$config = @include __DIR__ . '/config.php';
if (!$config || !hash_equals($config['poll_token'] ?? '', $_GET['token'] ?? '')) {
    http_response_code(403); exit('no');
}
$dir = __DIR__ . '/../doubled_state/pending';
$out = [];
if (is_dir($dir)) {
    foreach (glob($dir . '/*.json') as $f) {
        $d = json_decode(file_get_contents($f), true);
        if ($d && (time() - ($d['ts'] ?? 0)) < 600) { $out[] = $d; }
        @unlink($f);
    }
}
header('Content-Type: application/json');
echo json_encode($out);
