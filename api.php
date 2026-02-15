<?php
/**
 * iamtoxico Valet API Proxy
 * Handles Gemini requests for multi-category card generation
 */

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

// Configuration - same key as MelodicLabs
$GEMINI_API_KEY = getenv('GEMINI_API_KEY') ?: 'AIzaSyAJqwj8xU7bRjPWRZZBh6teDwQVbEjohSg';

// Get request body
$input = file_get_contents('php://input');
$data = json_decode($input, true);

$query = $data['query'] ?? '';
$anchor = $data['anchor'] ?? '';
$prefs = $data['prefs'] ?? [];

if (!$query) {
    http_response_code(400);
    echo json_encode(['error' => 'No query provided']);
    exit;
}

// Build the prompt for structured card generation
$prefsText = !empty($prefs) ? "User preferences: " . implode(', ', $prefs) . ". " : "";
$anchorText = $anchor ? "Music Anchor Seed: \"$anchor\". Use this as the vibe reference for song suggestions. " : "";

$systemPrompt = <<<PROMPT
You are a lifestyle valet assistant. Given a user query, detect the context and return exactly 6 recommendations in JSON format.

Categories to detect: vacation/travel, fashion, music, food, wellness, nightlife, shopping

For each query, return:
- 2 YouTube video suggestions (relevant to the topic)
- 2 contextual offers (hotels for travel, products for fashion, restaurants for food, etc.)
- 2 song suggestions that blend the user's anchor seed vibe with the query context

{$anchorText}{$prefsText}

User Query: "{$query}"

Respond ONLY with valid JSON in this exact format:
{
  "category": "travel",
  "cards": [
    {"slot": 1, "type": "youtube", "title": "Video Title", "subtitle": "Channel Name", "searchQuery": "youtube search terms"},
    {"slot": 2, "type": "youtube", "title": "Video Title", "subtitle": "Channel Name", "searchQuery": "youtube search terms"},
    {"slot": 3, "type": "offer", "title": "Hotel/Product Name", "subtitle": "Location/Brand", "searchQuery": "expedia or shopping search terms", "price": "$XXX"},
    {"slot": 4, "type": "offer", "title": "Hotel/Product Name", "subtitle": "Location/Brand", "searchQuery": "expedia or shopping search terms", "price": "$XXX"},
    {"slot": 5, "type": "song", "title": "Song Title", "artist": "Artist Name"},
    {"slot": 6, "type": "song", "title": "Song Title", "artist": "Artist Name"}
  ]
}
PROMPT;

// Call Gemini
$url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={$GEMINI_API_KEY}";

$payload = [
    'contents' => [
        ['parts' => [['text' => $systemPrompt]]]
    ],
    'generationConfig' => [
        'temperature' => 0.8,
        'maxOutputTokens' => 2000
    ]
];

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

if (curl_errno($ch)) {
    http_response_code(500);
    echo json_encode(['error' => 'Curl error: ' . curl_error($ch)]);
    curl_close($ch);
    exit;
}

curl_close($ch);

$json = json_decode($response, true);

if (isset($json['candidates'][0]['content']['parts'][0]['text'])) {
    $text = $json['candidates'][0]['content']['parts'][0]['text'];
    
    // Extract JSON from response (handle markdown code blocks)
    $text = preg_replace('/```json\s*/', '', $text);
    $text = preg_replace('/```\s*/', '', $text);
    $text = trim($text);
    
    $parsed = json_decode($text, true);
    
    if ($parsed) {
        echo json_encode($parsed);
    } else {
        // Return raw text if JSON parse fails
        echo json_encode(['error' => 'Failed to parse AI response', 'raw' => $text]);
    }
} else {
    http_response_code($httpCode);
    echo $response;
}
?>
