<?php
// Planning-note drain for the Studio poller (token-gated). Returns + removes
// notes submitted from the Notes tab so Hermes can record them.
$config = @include __DIR__ . '/config.php';
if (!$config || !hash_equals($config['poll_token'] ?? '', $_GET['token'] ?? '')) {
    http_response_code(403); exit('no');
}
$dir = __DIR__ . '/../doubled_state/notes';
$out = [];
if (is_dir($dir)) {
    foreach (glob($dir . '/*.json') as $f) {
        $d = json_decode(file_get_contents($f), true);
        if ($d) { $out[] = $d; }
        @unlink($f);
    }
}
header('Content-Type: application/json');
echo json_encode($out);
