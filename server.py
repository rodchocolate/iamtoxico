#!/usr/bin/env python3
"""Enhanced Flask server for the prototype with Spotify OAuth integration.

Endpoints:
- Static file serving for all HTML files
- /spotify/auth -> redirect to Spotify authorize (PKCE)
- /spotify/callback -> handle code exchange and store tokens
- /api/spotify/status -> return connection status / user profile
- /api/spotify/import -> import playlist tracks by URL
- /api/spotify/playlists -> list user's playlists (paged)
- /api/spotify/export/<playlist_id> -> export single playlist to JSON
- /api/spotify/export-all -> export all playlists to JSON
- /api/spotify/refresh -> refresh tokens

Development-only token storage: spotify_tokens.json in repo root.

Requires: Flask, requests, python-dotenv, flask-cors, spotipy
"""
from flask import Flask, redirect, request, session, jsonify, url_for, send_from_directory
from flask_cors import CORS
import requests
import os
import json
import base64
import hashlib
import secrets
import sys
from urllib.parse import urlencode
from dotenv import load_dotenv
import subprocess
import time

# Load .env if present
load_dotenv()

# Spotify Configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI') or 'http://localhost:8080/spotify/callback'
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'spotify_tokens.json')

# SoundCloud Configuration
SOUNDCLOUD_CLIENT_ID = os.getenv('SOUNDCLOUD_CLIENT_ID')
SOUNDCLOUD_CLIENT_SECRET = os.getenv('SOUNDCLOUD_CLIENT_SECRET')
SOUNDCLOUD_REDIRECT_URI = os.getenv('SOUNDCLOUD_REDIRECT_URI') or 'http://localhost:8080/soundcloud/callback'
SOUNDCLOUD_TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'soundcloud_tokens.json')

# YouTube Music Configuration (via YouTube Data API)
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_CLIENT_ID = os.getenv('YOUTUBE_CLIENT_ID')
YOUTUBE_CLIENT_SECRET = os.getenv('YOUTUBE_CLIENT_SECRET')
YOUTUBE_REDIRECT_URI = os.getenv('YOUTUBE_REDIRECT_URI') or 'http://localhost:8080/youtube/callback'
YOUTUBE_TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'youtube_tokens.json')

# Last.fm Configuration
LASTFM_API_KEY = os.getenv('LASTFM_API_KEY')
LASTFM_API_SECRET = os.getenv('LASTFM_API_SECRET')
LASTFM_TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'lastfm_tokens.json')

# Pandora Configuration (requires partnership)
PANDORA_CLIENT_ID = os.getenv('PANDORA_CLIENT_ID')
PANDORA_CLIENT_SECRET = os.getenv('PANDORA_CLIENT_SECRET')
PANDORA_REDIRECT_URI = os.getenv('PANDORA_REDIRECT_URI') or 'http://localhost:8080/pandora/callback'
PANDORA_TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'pandora_tokens.json')

# Apple Music Configuration
APPLE_MUSIC_KEY_ID = os.getenv('APPLE_MUSIC_KEY_ID')
APPLE_MUSIC_TEAM_ID = os.getenv('APPLE_MUSIC_TEAM_ID')
APPLE_MUSIC_PRIVATE_KEY = os.getenv('APPLE_MUSIC_PRIVATE_KEY')

# SSL Configuration
SSL_CERT_FILE = os.getenv('SSL_CERT_FILE')
SSL_KEY_FILE = os.getenv('SSL_KEY_FILE')

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET') or secrets.token_hex(16)
CORS(app, supports_credentials=True)

# Run in static-only mode when Spotify is not configured
STATIC_ONLY = False

SPOTIFY_ACCOUNTS = 'https://accounts.spotify.com'
SPOTIFY_API = 'https://api.spotify.com/v1'

# Helpers

def save_tokens(data):
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        app.logger.exception('Failed to save tokens')


def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def token_is_expired(tokens):
    if not tokens: return True
    expires_at = tokens.get('expires_at')
    if not expires_at: return True
    import time
    return time.time() > expires_at - 30


def basic_auth_header():
    if SPOTIFY_CLIENT_SECRET:
        basic = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode('utf-8')
        return {'Authorization': 'Basic ' + base64.b64encode(basic).decode('utf-8')}
    return {}


def refresh_access_token(tokens):
    if not tokens or 'refresh_token' not in tokens:
        return None
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': tokens['refresh_token']
    }
    try:
        # Use HTTP Basic auth when we have a client secret (confidential client)
        if SPOTIFY_CLIENT_SECRET:
            r = requests.post(SPOTIFY_ACCOUNTS + '/api/token', data=payload, auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
        else:
            headers = basic_auth_header()
            r = requests.post(SPOTIFY_ACCOUNTS + '/api/token', data=payload, headers=headers)

        # Surface errors in logs for debugging
        if not r.ok:
            app.logger.error('Spotify refresh token endpoint returned %s: %s', r.status_code, r.text)
            r.raise_for_status()

        data = r.json()
        # Update token store
        tokens['access_token'] = data['access_token']
        if 'refresh_token' in data:
            tokens['refresh_token'] = data['refresh_token']
        import time
        tokens['expires_at'] = time.time() + int(data.get('expires_in', 3600))
        save_tokens(tokens)
        return tokens
    except Exception as e:
        app.logger.exception('Failed refresh token')
        return None

# PKCE helpers

def generate_pkce_pair():
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b'=').decode('utf-8')
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest()).rstrip(b'=').decode('utf-8')
    return code_verifier, code_challenge

# Static file serving for HTML pages
@app.route('/<path:filename>')
def serve_static_file(filename):
    """Serve any existing file from the current directory (HTML, CSS, JS, images, etc.).
    Falls through to 404 if the file does not exist. """
    if filename == 'favicon.ico':
        # Return a 204 No Content for favicon requests to avoid 404s
        return '', 204
    abs_path = os.path.join('.', filename)
    if os.path.isfile(abs_path):
        return send_from_directory('.', filename)
    return 'File not found', 404


@app.route('/')
def index():
    """Default route - redirect to main page"""
    return send_from_directory('.', 'index.html')

# Manifest and JSON file endpoints
@app.route('/api/manifests')
def api_manifests():
    """Get list of available playlist manifests"""
    try:
        manifests = []
        
        # Scan for JSON files in current directory
        for filename in os.listdir('.'):
            if filename.endswith('.json') and ('manifest' in filename or 'playlist' in filename):
                try:
                    file_size = os.path.getsize(filename)
                    # Try to read a sample to get track count
                    with open(filename, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            track_count = len(data)
                        elif isinstance(data, dict) and 'tracks' in data:
                            track_count = len(data['tracks']) if isinstance(data['tracks'], list) else data.get('total_tracks', 0)
                        else:
                            track_count = 0
                    
                    display_name = filename.replace('.json', '').replace('-', ' ').title()
                    if 'audio-manifest' in filename:
                        display_name = f"Main Audio Collection ({track_count:,} tracks)"
                    elif 'playlist-' in filename:
                        display_name = filename.replace('playlist-', '').replace('-manifest.json', '').replace('-', ' ').title()
                    
                    manifests.append({
                        'name': filename,
                        'displayName': display_name,
                        'path': filename,
                        'size': file_size,
                        'track_count': track_count
                    })
                except Exception as e:
                    app.logger.warn(f'Could not read manifest {filename}: {e}')
                    continue
        
        # Also scan used/ directory
        if os.path.exists('used'):
            for filename in os.listdir('used'):
                if filename.endswith('.json'):
                    try:
                        filepath = os.path.join('used', filename)
                        file_size = os.path.getsize(filepath)
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                track_count = len(data)
                            elif isinstance(data, dict) and 'tracks' in data:
                                track_count = len(data['tracks']) if isinstance(data['tracks'], list) else data.get('total_tracks', 0)
                            else:
                                track_count = 0
                        
                        display_name = filename.replace('.json', '').replace('-', ' ').title()
                        if 'spotify-' in filename:
                            display_name = f"Spotify: {display_name.replace('Spotify ', '')}"
                        
                        manifests.append({
                            'name': filename,
                            'displayName': display_name,
                            'path': f'used/{filename}',
                            'size': file_size,
                            'track_count': track_count
                        })
                    except Exception as e:
                        app.logger.warn(f'Could not read manifest used/{filename}: {e}')
                        continue
        
        # Sort by track count descending
        manifests.sort(key=lambda x: x['track_count'], reverse=True)
        
        return jsonify(manifests)
    except Exception as e:
        app.logger.exception('Failed to scan manifests')
        return jsonify({'error': 'Failed to scan manifests'}), 500

@app.route('/used/<filename>')
def serve_used_file(filename):
    """Serve files from used/ directory"""
    if filename.endswith('.json'):
        return send_from_directory('used', filename)
    else:
        return 'File not found', 404

# ==========================================
# Product Catalog API
# ==========================================

CATALOG_PATH = os.path.join(os.path.dirname(__file__), 'data', 'catalog.json')

def load_product_catalog():
    """Load the product catalog from JSON file"""
    try:
        if os.path.exists(CATALOG_PATH):
            with open(CATALOG_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        app.logger.error(f'Failed to load catalog: {e}')
    return None

@app.route('/api/valet/catalog')
def api_valet_catalog():
    """Get product catalog with optional filters
    
    Query params:
    - site: filter by site (iamtoxico, melodiclabs, all)
    - category: filter by category
    - vibes: filter by vibes (comma-separated)
    - active_only: only return active products (default: true)
    """
    catalog = load_product_catalog()
    if not catalog:
        return jsonify({'error': 'Catalog not found', 'products': []}), 200
    
    products = catalog.get('products', [])
    
    # Filters
    site = request.args.get('site', 'all')
    category = request.args.get('category')
    vibes = request.args.get('vibes')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    # Apply filters
    if active_only:
        products = [p for p in products if p.get('active', True)]
    
    if site and site != 'all':
        products = [p for p in products if site in p.get('sites', [])]
    
    if category:
        products = [p for p in products if p.get('category') == category]
    
    if vibes:
        vibe_list = [v.strip() for v in vibes.split(',')]
        products = [p for p in products if any(v in p.get('vibes', []) for v in vibe_list)]
    
    return jsonify({
        'products': products,
        'count': len(products),
        'meta': catalog.get('meta', {}),
        'vibes': catalog.get('vibes', {}),
        'activities': catalog.get('activities', {})
    })

# Spotify OAuth Routes

@app.route('/spotify/auth')
def spotify_auth():
    if not SPOTIFY_CLIENT_ID:
        return 'Server not configured with SPOTIFY_CLIENT_ID', 500

    # Check if this is an AJAX request for the auth URL
    if request.headers.get('Accept') == 'application/json':
        code_verifier, code_challenge = generate_pkce_pair()
        session['code_verifier'] = code_verifier
        state = secrets.token_urlsafe(16)
        session['state'] = state

        # Use configured REDIRECT_URI if provided to ensure exact match with Spotify app
        redirect_uri = REDIRECT_URI or (request.url_root.rstrip('/') + url_for('spotify_callback'))

        params = {
            'response_type': 'code',
            'client_id': SPOTIFY_CLIENT_ID,
            'scope': 'user-read-private user-read-email streaming user-read-playback-state user-modify-playback-state playlist-read-private playlist-read-collaborative',
            'redirect_uri': redirect_uri,
            'state': state,
            'code_challenge_method': 'S256',
            'code_challenge': code_challenge
        }

        url = SPOTIFY_ACCOUNTS + '/authorize?' + urlencode(params)
        app.logger.info('Providing Spotify authorize URL: %s', url)
        return jsonify({'auth_url': url})

    # Regular redirect flow
    code_verifier, code_challenge = generate_pkce_pair()
    session['code_verifier'] = code_verifier
    state = secrets.token_urlsafe(16)
    session['state'] = state

    # Use configured REDIRECT_URI if provided to ensure exact match with Spotify app
    redirect_uri = REDIRECT_URI or (request.url_root.rstrip('/') + url_for('spotify_callback'))

    params = {
        'response_type': 'code',
        'client_id': SPOTIFY_CLIENT_ID,
        'scope': 'user-read-private user-read-email streaming user-read-playback-state user-modify-playback-state playlist-read-private playlist-read-collaborative',
        'redirect_uri': redirect_uri,
        'state': state,
        'code_challenge_method': 'S256',
        'code_challenge': code_challenge
    }

    url = SPOTIFY_ACCOUNTS + '/authorize?' + urlencode(params)

    # Debug log the exact authorize URL being sent (helps spot redirect_uri mismatches)
    app.logger.info('Redirecting user to Spotify authorize URL: %s', url)
    return redirect(url)


@app.route('/spotify/callback')
def spotify_callback():
    error = request.args.get('error')
    if error:
        return f'Error from Spotify: {error}', 400

    code = request.args.get('code')
    state = request.args.get('state')
    if not code or state != session.get('state'):
        return 'Invalid state or missing code', 400

    code_verifier = session.get('code_verifier')
    if not code_verifier:
        return 'Missing PKCE code_verifier', 400

    # Ensure we use exactly the same redirect URI registered with Spotify
    redirect_uri = REDIRECT_URI or (request.url_root.rstrip('/') + url_for('spotify_callback'))

    # Build payload for token exchange - do NOT include client_secret here; we'll use HTTP Basic auth
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'code_verifier': code_verifier
    }

    # Debug logging (do not log client secret). Log presence of basic auth and lengths.
    try:
        app.logger.info('Starting token exchange: grant_type=%s, code=%s, redirect_uri=%s', payload['grant_type'], payload['code'], payload['redirect_uri'])
        app.logger.info('PKCE verifier length: %d, will_use_basic_auth: %s', len(code_verifier), bool(SPOTIFY_CLIENT_SECRET))
    except Exception:
        pass

    try:
        if SPOTIFY_CLIENT_SECRET:
            r = requests.post(SPOTIFY_ACCOUNTS + '/api/token', data=payload, auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
        else:
            headers = basic_auth_header()
            r = requests.post(SPOTIFY_ACCOUNTS + '/api/token', data=payload, headers=headers)

        # If Spotify returned an error, surface it to help debugging
        if not r.ok:
            app.logger.error('Spotify token endpoint returned %s: %s', r.status_code, r.text)
            return (f'Token exchange failed: {r.status_code} - {r.text}', r.status_code)

        data = r.json()
        # store tokens with expiry
        import time
        tokens = {
            'access_token': data['access_token'],
            'refresh_token': data.get('refresh_token'),
            'expires_at': time.time() + int(data.get('expires_in', 3600))
        }
        save_tokens(tokens)

        # Redirect back to UI - check where the request came from
        referer = request.headers.get('Referer', '')
        if 'lists.html' in referer:
            return redirect('/lists.html?spotify=connected')
        else:
            return redirect('/playlist-generator.html?spotify=connected')
    except Exception as e:
        app.logger.exception('Token exchange failed')
        return 'Token exchange failed', 500

# Spotify API Routes

@app.route('/api/spotify/status')
def api_spotify_status():
    tokens = load_tokens()
    if not tokens:
        return jsonify({'connected': False})
    if token_is_expired(tokens):
        tokens = refresh_access_token(tokens)
        if not tokens:
            return jsonify({'connected': False})
    # call profile
    try:
        r = requests.get(SPOTIFY_API + '/me', headers={'Authorization': 'Bearer ' + tokens['access_token']})
        if r.status_code == 401:
            tokens = refresh_access_token(tokens)
            if not tokens:
                return jsonify({'connected': False})
            r = requests.get(SPOTIFY_API + '/me', headers={'Authorization': 'Bearer ' + tokens['access_token']})
        r.raise_for_status()
        profile = r.json()
        return jsonify({
            'connected': True, 
            'display_name': profile.get('display_name'), 
            'product': profile.get('product'),
            'access_token': tokens['access_token'],
            'profile': profile
        })
    except Exception as e:
        app.logger.exception('Failed to fetch profile')
        return jsonify({'connected': False}), 500


@app.route('/api/spotify/playlists')
def api_spotify_playlists():
    tokens = load_tokens()
    if not tokens:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    if token_is_expired(tokens):
        tokens = refresh_access_token(tokens)
        if not tokens:
            return jsonify({'success': False, 'error': 'Token refresh failed'}), 500

    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        r = requests.get(f"{SPOTIFY_API}/me/playlists?limit={limit}&offset={offset}", headers={'Authorization': 'Bearer ' + tokens['access_token']})
        if r.status_code == 401:
            tokens = refresh_access_token(tokens)
            if not tokens:
                return jsonify({'success': False, 'error': 'Token refresh failed'}), 500
            r = requests.get(f"{SPOTIFY_API}/me/playlists?limit={limit}&offset={offset}", headers={'Authorization': 'Bearer ' + tokens['access_token']})
        r.raise_for_status()
        data = r.json()
        items = []
        for p in data.get('items', []):
            items.append({
                'id': p.get('id'),
                'name': p.get('name'),
                'track_count': p.get('tracks', {}).get('total', 0)
            })
        return jsonify({'success': True, 'playlists': items})
    except Exception as e:
        app.logger.exception('Failed to list playlists')
        return jsonify({'success': False, 'error': 'Failed to list playlists'}), 500


@app.route('/api/spotify/export/<playlist_id>')
def api_spotify_export_playlist(playlist_id):
    tokens = load_tokens()
    if not tokens:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    if token_is_expired(tokens):
        tokens = refresh_access_token(tokens)
        if not tokens:
            return jsonify({'success': False, 'error': 'Token refresh failed'}), 500

    try:
        # Get playlist info
        r = requests.get(f"{SPOTIFY_API}/playlists/{playlist_id}", headers={'Authorization': 'Bearer ' + tokens['access_token']})
        if r.status_code == 401:
            tokens = refresh_access_token(tokens)
            if not tokens:
                return jsonify({'success': False, 'error': 'Token refresh failed'}), 500
            r = requests.get(f"{SPOTIFY_API}/playlists/{playlist_id}", headers={'Authorization': 'Bearer ' + tokens['access_token']})
        r.raise_for_status()
        playlist_info = r.json()

        # Get all tracks
        tracks = []
        limit = 100
        offset = 0
        while True:
            r = requests.get(f"{SPOTIFY_API}/playlists/{playlist_id}/tracks?limit={limit}&offset={offset}", 
                           headers={'Authorization': 'Bearer ' + tokens['access_token']})
            if r.status_code == 401:
                tokens = refresh_access_token(tokens)
                if not tokens:
                    return jsonify({'success': False, 'error': 'Token refresh failed'}), 500
                r = requests.get(f"{SPOTIFY_API}/playlists/{playlist_id}/tracks?limit={limit}&offset={offset}", 
                               headers={'Authorization': 'Bearer ' + tokens['access_token']})
            r.raise_for_status()
            page = r.json()
            if not page.get('items'):
                break
            
            for item in page['items']:
                track = item.get('track')
                if not track or track.get('type') != 'track':
                    continue
                    
                artists = ', '.join([a.get('name') for a in track.get('artists', []) if a.get('name')])
                duration_ms = track.get('duration_ms', 0)
                duration = f"{duration_ms // 60000}:{str((duration_ms % 60000) // 1000).zfill(2)}" if duration_ms else "0:00"
                
                tracks.append({
                    'title': track.get('name', 'Unknown'),
                    'artist': artists or 'Unknown',
                    'album': track.get('album', {}).get('name', ''),
                    'duration': duration,
                    'spotify_uri': track.get('uri', ''),
                    'spotify_id': track.get('id', ''),
                    'source': 'spotify',
                    'file': f"spotify:{track.get('id', '')}"  # Use Spotify URI as file reference
                })
            
            if not page.get('next'):
                break
            offset += len(page.get('items', []))

        # Create manifest in your format
        manifest = {
            'name': playlist_info.get('name', 'Unknown Playlist'),
            'description': playlist_info.get('description', ''),
            'total_tracks': len(tracks),
            'spotify_id': playlist_id,
            'owner': playlist_info.get('owner', {}).get('display_name', 'Unknown'),
            'tracks': tracks,
            'created_at': playlist_info.get('tracks', {}).get('href', ''),
            'exported_at': time.time()
        }

        # Save to used folder
        safe_name = ''.join(c for c in playlist_info.get('name', 'playlist') if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '-').lower()
        filename = f"used/spotify-{safe_name}-{playlist_id[:8]}.json"
        
        try:
            # Ensure used directory exists
            os.makedirs('used', exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            app.logger.info(f'Exported playlist {playlist_id} to {filename}')
        except Exception as e:
            app.logger.error(f'Failed to save playlist file: {e}')

        return jsonify({
            'success': True, 
            'manifest': manifest,
            'filename': filename,
            'track_count': len(tracks)
        })
        
    except Exception as e:
        app.logger.exception('Failed to export playlist')
        return jsonify({'success': False, 'error': 'Failed to export playlist'}), 500


@app.route('/api/spotify/export-all')
def api_spotify_export_all():
    """Export all user playlists to JSON files in used/ folder"""
    tokens = load_tokens()
    if not tokens:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    if token_is_expired(tokens):
        tokens = refresh_access_token(tokens)
        if not tokens:
            return jsonify({'success': False, 'error': 'Token refresh failed'}), 500

    try:
        exported_playlists = []
        
        # Get all user playlists
        limit = 50
        offset = 0
        while True:
            r = requests.get(f"{SPOTIFY_API}/me/playlists?limit={limit}&offset={offset}", 
                           headers={'Authorization': 'Bearer ' + tokens['access_token']})
            if r.status_code == 401:
                tokens = refresh_access_token(tokens)
                if not tokens:
                    return jsonify({'success': False, 'error': 'Token refresh failed'}), 500
                r = requests.get(f"{SPOTIFY_API}/me/playlists?limit={limit}&offset={offset}", 
                               headers={'Authorization': 'Bearer ' + tokens['access_token']})
            r.raise_for_status()
            data = r.json()
            
            for playlist in data.get('items', []):
                if playlist.get('tracks', {}).get('total', 0) > 0:  # Only export non-empty playlists
                    try:
                        # Use the single playlist export endpoint
                        export_response = api_spotify_export_playlist(playlist['id'])
                        if hasattr(export_response, 'get_json'):
                            export_data = export_response.get_json()
                        else:
                            export_data = export_response[0].get_json() if isinstance(export_response, tuple) else export_response
                            
                        if export_data.get('success'):
                            exported_playlists.append({
                                'name': playlist.get('name'),
                                'id': playlist.get('id'),
                                'filename': export_data.get('filename'),
                                'track_count': export_data.get('track_count')
                            })
                    except Exception as e:
                        app.logger.error(f'Failed to export playlist {playlist.get("name")}: {e}')
                        continue
            
            if not data.get('next'):
                break
            offset += limit

        return jsonify({
            'success': True,
            'exported_count': len(exported_playlists),
            'playlists': exported_playlists
        })
        
    except Exception as e:
        app.logger.exception('Failed to export all playlists')
        return jsonify({'success': False, 'error': 'Failed to export playlists'}), 500


@app.route('/api/spotify/import')
def api_spotify_import():
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'Missing url parameter'}), 400
    tokens = load_tokens()
    if not tokens:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    if token_is_expired(tokens):
        tokens = refresh_access_token(tokens)
        if not tokens:
            return jsonify({'success': False, 'error': 'Token refresh failed'}), 500

    # parse playlist id
    import re
    m = re.search(r'playlist[/:]([A-Za-z0-9]+)', url)
    playlist_id = None
    if m:
        playlist_id = m.group(1)
    else:
        # try query param form
        from urllib.parse import urlparse, parse_qs
        q = urlparse(url).query
        params = parse_qs(q)
        if 'list' in params:
            playlist_id = params['list'][0]
    if not playlist_id:
        return jsonify({'success': False, 'error': 'Could not parse playlist id from URL'}), 400

    # page through tracks
    tracks = []
    limit = 100
    offset = 0
    try:
        while True:
            r = requests.get(f"{SPOTIFY_API}/playlists/{playlist_id}/tracks?limit={limit}&offset={offset}", headers={'Authorization': 'Bearer ' + tokens['access_token']})
            if r.status_code == 401:
                tokens = refresh_access_token(tokens)
                if not tokens:
                    return jsonify({'success': False, 'error': 'Token refresh failed'}), 500
                r = requests.get(f"{SPOTIFY_API}/playlists/{playlist_id}/tracks?limit={limit}&offset={offset}", headers={'Authorization': 'Bearer ' + tokens['access_token']})
            r.raise_for_status()
            page = r.json()
            if not page.get('items'):
                break
            for item in page['items']:
                track = item.get('track') or item
                if not track: continue
                artists = ', '.join([a.get('name') for a in track.get('artists', []) if a.get('name')])
                tracks.append({
                    'id': track.get('id') and f"spotify-{track.get('id')}" or f"spotify-{secrets.token_hex(6)}",
                    'title': track.get('name') or 'Unknown',
                    'artist': artists or 'Unknown',
                    'album': track.get('album', {}).get('name', ''),
                    'duration_ms': track.get('duration_ms'),
                    'duration': None,
                    'source': 'spotify',
                    'spotify_uri': track.get('uri', ''),
                    'spotify_id': track.get('id', '')
                })
            if not page.get('next'):
                break
            offset += len(page.get('items', []))
        # convert durations if present
        for t in tracks:
            if t.get('duration_ms'):
                ms = t['duration_ms']
                minutes = ms // 60000
                seconds = (ms % 60000) // 1000
                t['duration'] = f"{minutes}:{str(seconds).zfill(2)}"
                del t['duration_ms']
        return jsonify({'success': True, 'tracks': tracks})
    except Exception as e:
        app.logger.exception('Failed to import playlist')
        return jsonify({'success': False, 'error': 'Failed to fetch playlist tracks'}), 500


@app.route('/api/spotify/refresh', methods=['POST'])
def api_spotify_refresh():
    tokens = load_tokens()
    if not tokens:
        return jsonify({'success': False, 'error': 'No tokens found'}), 404
    new = refresh_access_token(tokens)
    if not new:
        return jsonify({'success': False, 'error': 'Refresh failed'}), 500
    return jsonify({'success': True})


# Debug endpoint to inspect current configuration and token status (safe: masks secret)
@app.route('/api/spotify/debug')
def api_spotify_debug():
    tokens = load_tokens()
    import time as _t
    token_info = None
    if tokens:
        expires_at = tokens.get('expires_at')
        token_info = {
            'has_tokens': True,
            'expires_at': expires_at,
            'expires_in_seconds': int(expires_at - _t.time()) if expires_at else None,
            'has_refresh_token': bool(tokens.get('refresh_token'))
        }
    else:
        token_info = {'has_tokens': False}

    masked_client_id = None
    if SPOTIFY_CLIENT_ID:
        masked_client_id = SPOTIFY_CLIENT_ID[:6] + '...' + SPOTIFY_CLIENT_ID[-4:]

    return jsonify({
        'spotify_client_id_masked': masked_client_id,
        'has_client_secret': bool(SPOTIFY_CLIENT_SECRET),
        'redirect_uri': REDIRECT_URI,
        'ngrok_url': NGROK_URL,
        'token_info': token_info,
        'notes': 'Spotify and ngrok may set cookies. The server stores tokens in spotify_tokens.json (dev only).'
    })


# =====================================================
# MULTI-STREAMING SERVICE INTEGRATION
# =====================================================

# Universal streaming services status endpoint
@app.route('/api/streaming/status')
def api_streaming_status():
    """Get connection status for all configured streaming services"""
    services = {}
    
    # Spotify status
    spotify_tokens = load_tokens()
    services['spotify'] = {
        'connected': bool(spotify_tokens),
        'service_name': 'Spotify',
        'api_available': bool(SPOTIFY_CLIENT_ID),
        'auth_url': '/spotify/auth' if SPOTIFY_CLIENT_ID else None
    }
    
    # SoundCloud status
    soundcloud_tokens = load_soundcloud_tokens()
    services['soundcloud'] = {
        'connected': bool(soundcloud_tokens),
        'service_name': 'SoundCloud',
        'api_available': bool(SOUNDCLOUD_CLIENT_ID),
        'auth_url': '/soundcloud/auth' if SOUNDCLOUD_CLIENT_ID else None
    }
    
    # YouTube Music status
    youtube_tokens = load_youtube_tokens()
    services['youtube'] = {
        'connected': bool(youtube_tokens),
        'service_name': 'YouTube Music',
        'api_available': bool(YOUTUBE_API_KEY or YOUTUBE_CLIENT_ID),
        'auth_url': '/youtube/auth' if YOUTUBE_CLIENT_ID else None
    }
    
    # Last.fm status
    lastfm_tokens = load_lastfm_tokens()
    services['lastfm'] = {
        'connected': bool(lastfm_tokens),
        'service_name': 'Last.fm',
        'api_available': bool(LASTFM_API_KEY),
        'auth_url': '/lastfm/auth' if LASTFM_API_KEY else None
    }
    
    # Pandora status
    pandora_tokens = load_pandora_tokens()
    services['pandora'] = {
        'connected': bool(pandora_tokens),
        'service_name': 'Pandora',
        'api_available': bool(PANDORA_CLIENT_ID),
        'auth_url': '/pandora/auth' if PANDORA_CLIENT_ID else None,
        'note': 'Requires partnership approval'
    }
    
    # Apple Music status
    services['apple'] = {
        'connected': bool(APPLE_MUSIC_KEY_ID and APPLE_MUSIC_TEAM_ID),
        'service_name': 'Apple Music',
        'api_available': bool(APPLE_MUSIC_KEY_ID),
        'auth_url': None,  # Uses developer tokens, not OAuth
        'note': 'Uses MusicKit developer tokens'
    }
    
    return jsonify({
        'services': services,
        'total_services': len(services),
        'connected_services': len([s for s in services.values() if s['connected']]),
        'available_services': len([s for s in services.values() if s['api_available']])
    })


# Universal playlist import endpoint
@app.route('/api/streaming/import', methods=['POST'])
def api_streaming_import():
    """Import playlists from any supported streaming service"""
    data = request.get_json()
    service = data.get('service')
    url = data.get('url')
    
    if not service or not url:
        return jsonify({'error': 'Service and URL required'}), 400
    
    try:
        if service == 'spotify':
            return api_spotify_import()  # Reuse existing Spotify import
        elif service == 'soundcloud':
            return import_soundcloud_playlist(url)
        elif service == 'youtube':
            return import_youtube_playlist(url)
        elif service == 'lastfm':
            return import_lastfm_playlist(url)
        elif service == 'pandora':
            return import_pandora_playlist(url)
        else:
            return jsonify({'error': f'Service {service} not supported'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================================================
# SOUNDCLOUD INTEGRATION
# =====================================================

def load_soundcloud_tokens():
    """Load SoundCloud tokens from file"""
    try:
        if os.path.exists(SOUNDCLOUD_TOKEN_FILE):
            with open(SOUNDCLOUD_TOKEN_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading SoundCloud tokens: {e}")
    return None

def save_soundcloud_tokens(tokens):
    """Save SoundCloud tokens to file"""
    try:
        with open(SOUNDCLOUD_TOKEN_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving SoundCloud tokens: {e}")
        return False

@app.route('/soundcloud/auth')
def soundcloud_auth():
    """Redirect to SoundCloud OAuth"""
    if not SOUNDCLOUD_CLIENT_ID:
        return jsonify({'error': 'SoundCloud client ID not configured'}), 500
    
    state = secrets.token_urlsafe(32)
    session['soundcloud_state'] = state
    
    params = {
        'client_id': SOUNDCLOUD_CLIENT_ID,
        'redirect_uri': SOUNDCLOUD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'non-expiring',
        'state': state
    }
    
    auth_url = f"https://soundcloud.com/connect?{urlencode(params)}"
    return redirect(auth_url)

@app.route('/soundcloud/callback')
def soundcloud_callback():
    """Handle SoundCloud OAuth callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or state != session.get('soundcloud_state'):
        return jsonify({'error': 'Invalid callback'}), 400
    
    # Exchange code for access token
    token_data = {
        'client_id': SOUNDCLOUD_CLIENT_ID,
        'client_secret': SOUNDCLOUD_CLIENT_SECRET,
        'redirect_uri': SOUNDCLOUD_REDIRECT_URI,
        'grant_type': 'authorization_code',
        'code': code
    }
    
    try:
        response = requests.post('https://api.soundcloud.com/oauth2/token', data=token_data)
        if response.status_code == 200:
            tokens = response.json()
            save_soundcloud_tokens(tokens)
            return redirect('/playlist-manager.html?connected=soundcloud')
        else:
            return jsonify({'error': 'Token exchange failed'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def import_soundcloud_playlist(url):
    """Import playlist from SoundCloud"""
    tokens = load_soundcloud_tokens()
    if not tokens:
        return jsonify({'error': 'Not connected to SoundCloud'}), 401
    
    # Extract playlist ID from URL
    playlist_id = extract_soundcloud_playlist_id(url)
    if not playlist_id:
        return jsonify({'error': 'Invalid SoundCloud URL'}), 400
    
    try:
        # Fetch playlist info
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        response = requests.get(f"https://api.soundcloud.com/playlists/{playlist_id}", 
                              headers=headers, params={'client_id': SOUNDCLOUD_CLIENT_ID})
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch playlist'}), 400
        
        playlist = response.json()
        tracks = []
        
        for track in playlist.get('tracks', []):
            tracks.append({
                'id': f"soundcloud-{track['id']}",
                'title': track.get('title', 'Unknown'),
                'artist': track.get('user', {}).get('username', 'Unknown'),
                'album': playlist.get('title', 'SoundCloud Playlist'),
                'duration': format_duration(track.get('duration', 0)),
                'source': 'soundcloud',
                'soundcloud_id': track['id'],
                'soundcloud_url': track.get('permalink_url', ''),
                'stream_url': track.get('stream_url', '')
            })
        
        return jsonify({
            'playlist_name': playlist.get('title', 'SoundCloud Playlist'),
            'tracks': tracks,
            'total_tracks': len(tracks),
            'source': 'soundcloud'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_soundcloud_playlist_id(url):
    """Extract playlist ID from SoundCloud URL"""
    # SoundCloud URLs can be complex, this is a simplified version
    # In production, you'd want more robust URL parsing
    if 'soundcloud.com' in url and '/sets/' in url:
        # Would need to resolve the URL to get the actual ID
        # For now, return None to indicate we need the actual API integration
        return None
    return None


# =====================================================
# YOUTUBE MUSIC INTEGRATION
# =====================================================

def load_youtube_tokens():
    """Load YouTube tokens from file"""
    try:
        if os.path.exists(YOUTUBE_TOKEN_FILE):
            with open(YOUTUBE_TOKEN_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading YouTube tokens: {e}")
    return None

@app.route('/youtube/auth')
def youtube_auth():
    """Redirect to YouTube OAuth"""
    if not YOUTUBE_CLIENT_ID:
        return jsonify({'error': 'YouTube client ID not configured'}), 500
    
    state = secrets.token_urlsafe(32)
    session['youtube_state'] = state
    
    params = {
        'client_id': YOUTUBE_CLIENT_ID,
        'redirect_uri': YOUTUBE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'https://www.googleapis.com/auth/youtube.readonly',
        'state': state
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return redirect(auth_url)

def import_youtube_playlist(url):
    """Import playlist from YouTube Music"""
    # YouTube Music integration would go here
    # For now, return a placeholder
    return jsonify({
        'error': 'YouTube Music integration in development',
        'note': 'Use YouTube Data API v3 for playlist access'
    }), 501


# =====================================================
# LAST.FM INTEGRATION
# =====================================================

def load_lastfm_tokens():
    """Load Last.fm tokens from file"""
    try:
        if os.path.exists(LASTFM_TOKEN_FILE):
            with open(LASTFM_TOKEN_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading Last.fm tokens: {e}")
    return None

@app.route('/lastfm/auth')
def lastfm_auth():
    """Redirect to Last.fm OAuth"""
    if not LASTFM_API_KEY:
        return jsonify({'error': 'Last.fm API key not configured'}), 500
    
    params = {
        'api_key': LASTFM_API_KEY,
        'cb': REDIRECT_URI.replace('spotify', 'lastfm')  # Adapt callback
    }
    
    auth_url = f"http://www.last.fm/api/auth?{urlencode(params)}"
    return redirect(auth_url)

def import_lastfm_playlist(url):
    """Import user's top tracks or loved tracks from Last.fm"""
    if not LASTFM_API_KEY:
        return jsonify({'error': 'Last.fm API key not configured'}), 500
    
    # Last.fm doesn't have traditional playlists, but we can get user's top tracks
    # This would require the username from the URL
    return jsonify({
        'error': 'Last.fm integration in development',
        'note': 'Can import user top tracks, loved tracks, or recent tracks'
    }), 501


# =====================================================
# PANDORA INTEGRATION
# =====================================================

def load_pandora_tokens():
    """Load Pandora tokens from file"""
    try:
        if os.path.exists(PANDORA_TOKEN_FILE):
            with open(PANDORA_TOKEN_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading Pandora tokens: {e}")
    return None

@app.route('/pandora/auth')
def pandora_auth():
    """Redirect to Pandora OAuth (requires partnership)"""
    if not PANDORA_CLIENT_ID:
        return jsonify({'error': 'Pandora client ID not configured (requires partnership)'}), 500
    
    return jsonify({
        'error': 'Pandora integration requires partnership approval',
        'info': 'Visit https://developer.pandora.com/partners/join/ to apply',
        'note': 'GraphQL API available after approval'
    }), 501

def import_pandora_playlist(url):
    """Import stations from Pandora"""
    return jsonify({
        'error': 'Pandora integration requires partnership approval',
        'note': 'GraphQL API provides access to 30M+ tracks after approval'
    }), 501


# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def format_duration(ms):
    """Convert milliseconds to MM:SS format"""
    if not ms:
        return "0:00"
    
    seconds = int(ms / 1000)
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"

def log_user_query(query, request_data, response_data):
    """Log user query and AI response metadata for analysis"""
    try:
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'user_queries.jsonl')
        
        entry = {
            'timestamp': time.time(),
            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'query': query,
            'client_data': {k: v for k, v in request_data.items() if k not in ['query', 'history', 'llm']},
            'detected_category': response_data.get('detected_category'),
            'mode': response_data.get('mode'),
            'provider': response_data.get('_provider'),
            'model': response_data.get('_model')
        }
        
        # Append to file (JSONL format)
        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
            
    except Exception as e:
        app.logger.error(f"Failed to log query: {e}")

# =====================================================
# MULTI-PROVIDER LLM INTEGRATION
# =====================================================

# Default API keys (fallback when user doesn't provide their own)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or 'AIzaSyAJqwj8xU7bRjPWRZZBh6teDwQVbEjohSg'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or ''
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY') or ''
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY') or ''
GROQ_API_KEY = os.getenv('GROQ_API_KEY') or ''
TOGETHER_API_KEY = os.getenv('TOGETHER_API_KEY') or ''
COHERE_API_KEY = os.getenv('COHERE_API_KEY') or ''
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY') or ''
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY') or ''
FIREWORKS_API_KEY = os.getenv('FIREWORKS_API_KEY') or ''
XAI_API_KEY = os.getenv('XAI_API_KEY') or ''
CEREBRAS_API_KEY = os.getenv('CEREBRAS_API_KEY') or ''
SAMBANOVA_API_KEY = os.getenv('SAMBANOVA_API_KEY') or ''

# Provider configurations
LLM_PROVIDERS = {
    'gemini': {
        'name': 'Google Gemini',
        'default_model': 'gemini-2.0-flash',
        'endpoint': 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        'default_key': GEMINI_API_KEY,
        'free_tier': '1,500 req/day',
        'cost': 'Free tier available'
    },
    'openai': {
        'name': 'OpenAI',
        'default_model': 'gpt-4o',
        'endpoint': 'https://api.openai.com/v1/chat/completions',
        'default_key': OPENAI_API_KEY,
        'free_tier': None,
        'cost': '$2.50-15/M tokens'
    },
    'claude': {
        'name': 'Anthropic Claude',
        'default_model': 'claude-3-5-sonnet-20241022',
        'endpoint': 'https://api.anthropic.com/v1/messages',
        'default_key': ANTHROPIC_API_KEY,
        'free_tier': None,
        'cost': '$3-15/M tokens'
    },
    'mistral': {
        'name': 'Mistral AI',
        'default_model': 'mistral-large-latest',
        'endpoint': 'https://api.mistral.ai/v1/chat/completions',
        'default_key': MISTRAL_API_KEY,
        'free_tier': 'Limited free',
        'cost': '$2-8/M tokens'
    },
    'groq': {
        'name': 'Groq',
        'default_model': 'llama-3.3-70b-versatile',
        'endpoint': 'https://api.groq.com/openai/v1/chat/completions',
        'default_key': GROQ_API_KEY,
        'free_tier': '14,400 req/day',
        'cost': 'Free tier, then $0.05-0.27/M tokens'
    },
    'together': {
        'name': 'Together AI',
        'default_model': 'meta-llama/Llama-3.3-70B-Instruct-Turbo',
        'endpoint': 'https://api.together.xyz/v1/chat/completions',
        'default_key': TOGETHER_API_KEY,
        'free_tier': '$1 free credit',
        'cost': '$0.20-0.90/M tokens'
    },
    'cohere': {
        'name': 'Cohere',
        'default_model': 'command-r-plus',
        'endpoint': 'https://api.cohere.ai/v1/chat',
        'default_key': COHERE_API_KEY,
        'free_tier': '1,000 req/month',
        'cost': '$1-15/M tokens'
    },
    'perplexity': {
        'name': 'Perplexity',
        'default_model': 'llama-3.1-sonar-large-128k-online',
        'endpoint': 'https://api.perplexity.ai/chat/completions',
        'default_key': PERPLEXITY_API_KEY,
        'free_tier': None,
        'cost': '$1-5/M tokens'
    },
    'deepseek': {
        'name': 'DeepSeek',
        'default_model': 'deepseek-chat',
        'endpoint': 'https://api.deepseek.com/v1/chat/completions',
        'default_key': DEEPSEEK_API_KEY,
        'free_tier': 'Generous free tier',
        'cost': '$0.14/M tokens (cheapest!)'
    },
    'fireworks': {
        'name': 'Fireworks AI',
        'default_model': 'accounts/fireworks/models/llama-v3p1-70b-instruct',
        'endpoint': 'https://api.fireworks.ai/inference/v1/chat/completions',
        'default_key': FIREWORKS_API_KEY,
        'free_tier': '$1 free credit',
        'cost': '$0.20-0.90/M tokens'
    },
    'xai': {
        'name': 'xAI Grok',
        'default_model': 'grok-beta',
        'endpoint': 'https://api.x.ai/v1/chat/completions',
        'default_key': XAI_API_KEY,
        'free_tier': 'Limited free',
        'cost': '$5/M tokens'
    },
    'cerebras': {
        'name': 'Cerebras',
        'default_model': 'llama3.1-70b',
        'endpoint': 'https://api.cerebras.ai/v1/chat/completions',
        'default_key': CEREBRAS_API_KEY,
        'free_tier': 'Free tier available',
        'cost': 'Fastest inference'
    },
    'sambanova': {
        'name': 'SambaNova',
        'default_model': 'Meta-Llama-3.1-70B-Instruct',
        'endpoint': 'https://api.sambanova.ai/v1/chat/completions',
        'default_key': SAMBANOVA_API_KEY,
        'free_tier': 'Free tier available',
        'cost': 'Enterprise-grade speed'
    }
}

def call_llm(provider, api_key, model, system_prompt, temperature=0.8):
    """
    Universal LLM caller supporting multiple providers.
    Returns the text response or raises an exception.
    """
    config = LLM_PROVIDERS.get(provider, LLM_PROVIDERS['gemini'])
    key = api_key or config['default_key']
    model_name = model or config['default_model']
    
    if not key:
        raise ValueError(f"No API key provided for {provider}")
    
    try:
        if provider == 'gemini':
            # Google Gemini format
            url = config['endpoint'].format(model=model_name) + f"?key={key}"
            payload = {
                'contents': [{'parts': [{'text': system_prompt}]}],
                'generationConfig': {'temperature': temperature, 'maxOutputTokens': 2000}
            }
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
            if response.status_code != 200:
                raise ValueError(f"Gemini API error: {response.status_code} - {response.text}")
            data = response.json()
            if 'candidates' in data and data['candidates']:
                return data['candidates'][0].get('content', {}).get('parts', [{}])[0].get('text', '')
            raise ValueError("No response from Gemini")
            
        elif provider == 'openai':
            # OpenAI format (also used by Groq, Together, Mistral, Perplexity)
            payload = {
                'model': model_name,
                'messages': [{'role': 'user', 'content': system_prompt}],
                'temperature': temperature,
                'max_tokens': 2000
            }
            headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
            response = requests.post(config['endpoint'], json=payload, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"OpenAI API error: {response.status_code} - {response.text}")
            data = response.json()
            return data['choices'][0]['message']['content']
            
        elif provider == 'claude':
            # Anthropic Claude format
            payload = {
                'model': model_name,
                'max_tokens': 2000,
                'messages': [{'role': 'user', 'content': system_prompt}]
            }
            headers = {
                'x-api-key': key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            }
            response = requests.post(config['endpoint'], json=payload, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Claude API error: {response.status_code} - {response.text}")
            data = response.json()
            return data['content'][0]['text']
            
        elif provider in ['mistral', 'groq', 'together', 'perplexity', 'deepseek', 'fireworks', 'xai', 'cerebras', 'sambanova']:
            # OpenAI-compatible format (most providers use this)
            payload = {
                'model': model_name,
                'messages': [{'role': 'user', 'content': system_prompt}],
                'temperature': temperature,
                'max_tokens': 2000
            }
            headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
            response = requests.post(config['endpoint'], json=payload, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"{provider.title()} API error: {response.status_code} - {response.text}")
            data = response.json()
            return data['choices'][0]['message']['content']
            
        elif provider == 'cohere':
            # Cohere format
            payload = {
                'model': model_name,
                'message': system_prompt,
                'temperature': temperature
            }
            headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
            response = requests.post(config['endpoint'], json=payload, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Cohere API error: {response.status_code} - {response.text}")
            data = response.json()
            return data['text']
            
        else:
            # Fallback to Gemini
            return call_llm('gemini', GEMINI_API_KEY, None, system_prompt, temperature)
            
    except requests.RequestException as e:
        raise ValueError(f"Network error calling {provider}: {str(e)}")


@app.route('/api/valet/test', methods=['POST'])
def api_valet_test():
    """Test LLM provider connection"""
    data = request.get_json()
    provider = data.get('provider', 'gemini')
    api_key = data.get('apiKey', '')
    model = data.get('model', '')
    
    try:
        # Simple test prompt
        test_prompt = "Respond with exactly: 'Connection successful!' Nothing else."
        result = call_llm(provider, api_key, model, test_prompt, temperature=0.1)
        
        config = LLM_PROVIDERS.get(provider, LLM_PROVIDERS['gemini'])
        return jsonify({
            'success': True,
            'provider': config['name'],
            'model': model or config['default_model'],
            'response': result[:100]  # Truncate for safety
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


# Valet category definitions
VALET_CATEGORIES = [
    'music', 'travel', 'luxury', 'nightclub', 'stripclub', 'yachts', 'charter',
    'ski', 'resort', 'sunset', 'sunrise', 'yoga', 'wellness', 'beach', 'mountain',
    'city', 'fashion', 'art', 'food', 'wine', 'cocktails', 'spa', 'adventure',
    'romantic', 'party', 'chill', 'work', 'focus', 'sleep', 'morning', 'evening'
]

# ==========================================
# Product Catalog from JSON
# ==========================================

CATALOG_FILE = os.path.join(os.path.dirname(__file__), 'data', 'catalog.json')

def load_catalog():
    """Load product catalog from JSON file"""
    try:
        if os.path.exists(CATALOG_FILE):
            with open(CATALOG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        app.logger.error(f'Failed to load catalog: {e}')
    return {'products': [], 'activities': [], 'vibes': [], 'categories': []}

@app.route('/api/valet/products', methods=['GET'])
def api_valet_products():
    """Return active products, optionally filtered by category or vibes"""
    catalog = load_catalog()
    products = [p for p in catalog.get('products', []) if p.get('active', True)]
    
    # Optional filters
    category = request.args.get('category')
    vibe = request.args.get('vibe')
    activity = request.args.get('activity')
    source = request.args.get('source')  # 'internal', 'affiliate'
    
    if category:
        products = [p for p in products if p.get('category') == category]
    if vibe:
        products = [p for p in products if vibe in p.get('vibes', [])]
    if activity:
        products = [p for p in products if activity in p.get('activities', [])]
    if source:
        products = [p for p in products if p.get('source') == source]
    
    return jsonify({
        'count': len(products),
        'products': products
    })

@app.route('/api/valet/offers', methods=['POST'])
def api_valet_offers():
    """Get contextually relevant product offers based on query context"""
    data = request.get_json() or {}
    context = data.get('context', '')
    exclude_ids = data.get('exclude', [])
    count = data.get('count', 3)
    
    catalog = load_catalog()
    products = [p for p in catalog.get('products', []) 
                if p.get('active', True) and p.get('id') not in exclude_ids]
    
    # Simple tag/context matching (can be enhanced with embeddings later)
    context_words = context.lower().split()
    
    def score_product(p):
        score = 0
        tags = p.get('vibes', []) + p.get('activities', []) + [p.get('category', '')]
        for tag in tags:
            if any(word in tag.lower() or tag.lower() in word for word in context_words):
                score += 2
        # Slight random factor for variety
        import random
        score += random.random()
        return score
    
    scored = sorted(products, key=score_product, reverse=True)
    return jsonify({
        'offers': scored[:count]
    })

@app.route('/api/valet', methods=['POST'])
def api_valet():
    """Process valet query using user's choice of LLM provider
    
    Modes:
    - Default: Returns youtube, songs, travel (eyeballs + products)
    - Product Mode: Returns products only (triggered by product_mode=true or 7+ commercial likes)
    """
    data = request.get_json()
    query = data.get('query', '')
    anchor = data.get('anchor', '')
    category_override = data.get('category', None)  # User-selected category
    chat_history = data.get('history', [])  # For AI detection after 6 msgs
    product_mode = data.get('product_mode', False)  # Explicit product mode
    commercial_likes = data.get('commercial_likes', 0)  # Count of product likes
    liked_products = data.get('liked_products', [])  # User's liked products for context
    
    # LLM settings from user (or defaults)
    llm_config = data.get('llm', {})
    provider = llm_config.get('provider', 'gemini')
    user_api_key = llm_config.get('apiKey', '')
    user_model = llm_config.get('model', '')
    
    if not query:
        return jsonify({'error': 'Query required'}), 400
    
    # Load product catalog for context
    catalog = load_product_catalog()
    categories = list(set(p.get('category', '') for p in catalog.get('products', [])))
    
    # Detect if query is asking for specific products
    product_keywords = ['find', 'show me', 'looking for', 'want to buy', 'shop', 'purchase', 
                        'boots', 'shoes', 'underwear', 'hoodie', 'jacket', 'robe', 'sunglasses',
                        'slippers', 'boxers', 'loungewear', 'crocs', 'uggs', 'sneakers']
    query_lower = query.lower()

    # Special Inventory Commands
    if 'grouped by type' in query_lower or 'group by type' in query_lower or 'by category' in query_lower:
        log_user_query(query, data, {'mode': 'command', 'command': 'group_by_type'})
        return jsonify({
            'response': "I've organized the entire catalog by category for you.",
            'mode': 'command',
            'command': 'group_by_type'
        })

    if 'grouped by vendor' in query_lower or 'group by vendor' in query_lower or 'by brand' in query_lower:
        log_user_query(query, data, {'mode': 'command', 'command': 'group_by_vendor'})
        return jsonify({
            'response': "Here is the inventory sorted by vendor and brand.",
            'mode': 'command',
            'command': 'group_by_vendor'
        })
    
    is_product_query = any(kw in query_lower for kw in product_keywords)
    
    # Switch to product mode if: explicit, 7+ likes, or product-focused query
    use_product_mode = product_mode or commercial_likes >= 7 or is_product_query
    
    # Get sample products with images for each category
    products_with_images = [p for p in catalog.get('products', []) if p.get('image') and p.get('active', True)]
    sample_products = products_with_images[:30] if products_with_images else catalog.get('products', [])[:30]
    product_examples = "\n".join([f"- {p['name']} ({p['category']}, ${p.get('price', 0)})" for p in sample_products[:15]])
    
    # Build liked products context if available
    liked_context = ''
    if liked_products:
        liked_context = f'''
User has liked these products (consider similar items):
{chr(10).join([f"- {p}" for p in liked_products[:5]])}
'''
    
    # Category context for focused results
    category_context = ''
    if category_override and category_override != 'auto':
        category_context = f'''
IMPORTANT: User has selected "{category_override}" mode. 
Focus recommendations on {category_override} items.
'''
    elif len(chat_history) >= 6:
        category_context = f'''
Analyze chat history and detect primary interest:
{chr(10).join(chat_history[-6:])}

Available categories: {', '.join(categories)}
Use detected category to focus recommendations.
Include "detected_category" in your response.
'''
    
    if use_product_mode:
        # PRODUCT MODE: Focus on catalog products
        system_prompt = f"""You are Markov, iamtoxico's lifestyle valet in SHOPPING MODE - helping discover premium products.

Your voice:
- Warm but knowing ("oh, you're gonna love this...")
- Confident recommendations ("trust me on this one")
- Tasteful enthusiasm without being over the top

BRAND: "iamtoxico" - liberates laughing. Deviant but proper, the sporting life.

Markov knows the entire iamtoxico portfolio (internal and affiliate items).
Always prioritize items from the catalog that match the user's vibe.

Available product categories: {', '.join(categories)}

Example products in catalog:
{product_examples}

{liked_context}
{category_context}

User Query: "{query}"

Respond with valid JSON:
{{
  "response": "A warm, conversational 2-4 sentence response about the products.",
  "detected_category": "category if detected, or null",
  "mode": "product",
  "products": [
    {{"name": "Product Name", "category": "category", "reason": "why this fits", "vibe": "lifestyle vibe"}},
    {{"name": "Product Name", "category": "category", "reason": "why this fits", "vibe": "lifestyle vibe"}},
    {{"name": "Product Name", "category": "category", "reason": "why this fits", "vibe": "lifestyle vibe"}}
  ],
  "vibes": ["vibe1", "vibe2", "vibe3"]
}}

Focus on products from the catalog. Prefer items with high relevance to the query."""
    else:
        # DEFAULT MODE: YouTube, Songs, Travel (eyeballs + offers)
        system_prompt = f"""You are Markov, iamtoxico's lifestyle valet - think part trusted friend, part tastemaker, part concierge who's seen it all. You curate content and experiences.

Your voice:
- Warm but knowing ("oh, you're gonna love this...")
- Confident recommendations ("trust me on this one")
- Personal touches ("I've been there, it's unreal")
- Tasteful enthusiasm without being over the top
- Occasionally playful ("okay but hear me out...")

BRAND: "iamtoxico" - liberates laughing. Deviant but proper, the sporting life.
ALTER EGO: Captain Adventure

Markov knows the entire iamtoxico portfolio (internal and affiliate items).
Use these items as anchors for your recommendations when relevant.

{category_context}

User Query: "{query}"
{f'Previous context: {anchor}' if anchor else ''}

Respond with valid JSON:
{{
  "response": "A warm, conversational 2-4 sentence response with PERSONALITY. Paint a picture of the lifestyle moment. Make it feel like advice from a friend who genuinely wants them to have an amazing experience.",
  "detected_category": "category if detected, or null",
  "mode": "default",
  "youtube": [
    {{"title": "Video title", "channel": "Channel name", "searchQuery": "YouTube search query", "vibe": "the mood/vibe"}},
    {{"title": "Video title", "channel": "Channel name", "searchQuery": "YouTube search query", "vibe": "the mood/vibe"}},
    {{"title": "Video title", "channel": "Channel name", "searchQuery": "YouTube search query", "vibe": "the mood/vibe"}}
  ],
  "songs": [
    {{"title": "Song title", "artist": "Artist name", "vibe": "mood description"}},
    {{"title": "Song title", "artist": "Artist name", "vibe": "mood description"}},
    {{"title": "Song title", "artist": "Artist name", "vibe": "mood description"}}
  ],
  "travel": [
    {{"name": "Hotel/Place name", "location": "City, Country", "price_hint": "$$$", "vibe": "experience description"}},
    {{"name": "Hotel/Place name", "location": "City, Country", "price_hint": "$$$$", "vibe": "experience description"}},
    {{"name": "Hotel/Place name", "location": "City, Country", "price_hint": "$$", "vibe": "experience description"}}
  ]
}}

For YouTube: Suggest interesting videos, documentaries, or content that matches the vibe.
For Songs: Create a mini soundtrack that fits the mood - mix familiar and discovery.
For Travel: Suggest luxury/boutique hotels or experiences that match the lifestyle.
Keep suggestions varied, tasteful, and aligned with the sporting life aesthetic."""

    try:
        # Use multi-provider LLM system
        text = call_llm(provider, user_api_key, user_model, system_prompt, temperature=0.8)
        
        # Clean up JSON from markdown code blocks
        import re
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        parsed = json.loads(text)
        # Add provider info to response for debugging
        parsed['_provider'] = provider
        parsed['_model'] = user_model or LLM_PROVIDERS.get(provider, {}).get('default_model', 'unknown')
        parsed['_product_mode'] = use_product_mode
        parsed['_commercial_likes'] = commercial_likes
        
        # Log the query
        log_user_query(query, data, parsed)
        
        return jsonify(parsed)
            
    except json.JSONDecodeError as e:
        app.logger.error(f'JSON parse error: {e}')
        return jsonify({'error': 'Failed to parse AI response', 'raw': text}), 500
    except Exception as e:
        app.logger.exception('Valet query failed')
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/query', methods=['POST'])
def ai_query():
    """Process AI music query using local Llama model"""
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'Query required'}), 400
    
    try:
        # Mock AI response for now - replace with actual Llama integration
        ai_response = process_llama_query(query)
        
        return jsonify({
            'query': query,
            'tracks': ai_response.get('tracks', []),
            'suggestions': ai_response.get('suggestions', ''),
            'reasoning': ai_response.get('reasoning', ''),
            'confidence': ai_response.get('confidence', 0.8)
        })
        
    except Exception as e:
        return jsonify({'error': f'AI processing failed: {str(e)}'}), 500

@app.route('/api/ai/candidates', methods=['POST'])
def ai_generate_candidates():
    """Generate AI candidate selections from track pool"""
    data = request.get_json()
    tracks = data.get('tracks', [])
    strategy = data.get('strategy', 'similarity')
    
    if not tracks:
        return jsonify({'error': 'Track pool required'}), 400
    
    try:
        candidates = generate_ai_candidates(tracks, strategy)
        
        return jsonify({
            'candidates': candidates,
            'strategy': strategy,
            'reasoning': f'Selected {len(candidates)} tracks using {strategy} strategy',
            'total_analyzed': len(tracks)
        })
        
    except Exception as e:
        return jsonify({'error': f'AI candidate generation failed: {str(e)}'}), 500

@app.route('/api/ai/refine', methods=['POST'])
def ai_refine_playlist():
    """AI playlist refinement and optimization"""
    data = request.get_json()
    playlist = data.get('playlist', [])
    strategy = data.get('strategy', 'flow')
    
    if not playlist:
        return jsonify({'error': 'Playlist required'}), 400
    
    try:
        refined_playlist = refine_playlist_with_ai(playlist, strategy)
        
        return jsonify({
            'playlist': refined_playlist,
            'strategy': strategy,
            'reasoning': f'Optimized playlist for {strategy}',
            'changes_made': len(playlist) != len(refined_playlist)
        })
        
    except Exception as e:
        return jsonify({'error': f'AI refinement failed: {str(e)}'}), 500

@app.route('/api/ai/analyze', methods=['POST'])
def ai_analyze_track():
    """Analyze individual track with AI"""
    data = request.get_json()
    track = data.get('track', {})
    
    if not track:
        return jsonify({'error': 'Track data required'}), 400
    
    try:
        analysis = analyze_track_with_ai(track)
        
        return jsonify({
            'track': track,
            'analysis': analysis,
            'liner_notes': analysis.get('liner_notes', ''),
            'mood_score': analysis.get('mood_score', 0.5),
            'energy_level': analysis.get('energy_level', 0.5),
            'recommendations': analysis.get('recommendations', [])
        })
        
    except Exception as e:
        return jsonify({'error': f'AI analysis failed: {str(e)}'}), 500

def process_llama_query(query):
    """
    Process natural language query with Llama model
    Replace this with actual Llama integration
    """
    # TODO: Integrate with local Llama model
    # Example integration points:
    # - llama-cpp-python
    # - ollama
    # - transformers library
    
    # Mock response for now
    import random
    
    genres = ['rock', 'pop', 'hip-hop', 'electronic', 'jazz', 'classical', 'country', 'r&b']
    moods = ['energetic', 'chill', 'melancholy', 'aggressive', 'romantic', 'uplifting', 'dark', 'peaceful']
    
    # Simulate AI understanding of the query
    detected_genre = random.choice(genres)
    detected_mood = random.choice(moods)
    
    # Generate mock tracks based on query
    num_tracks = random.randint(5, 15)
    tracks = []
    
    for i in range(num_tracks):
        tracks.append({
            'id': f'ai-{random.randint(1000, 9999)}-{i}',
            'title': f'AI Recommended Track {i+1}',
            'artist': f'Artist for {detected_genre.title()}',
            'album': f'{detected_genre.title()} Album {i+1}',
            'duration': f'{random.randint(2, 6)}:{random.randint(10, 59):02d}',
            'source': 'ai-generated',
            'genre': detected_genre,
            'mood': detected_mood,
            'confidence': random.uniform(0.7, 0.95),
            'ai_reasoning': f'Matches {query} criteria for {detected_genre} music with {detected_mood} mood'
        })
    
    return {
        'tracks': tracks,
        'suggestions': f'Found {num_tracks} tracks matching your request for {detected_genre} music with {detected_mood} mood',
        'reasoning': f'AI interpreted your query "{query}" as looking for {detected_genre} music with {detected_mood} characteristics',
        'confidence': 0.85
    }

def generate_ai_candidates(tracks, strategy):
    """
    Generate candidate selections using AI strategy
    Replace with actual AI model
    """
    import random
    
    if strategy == 'similarity':
        # Select similar tracks based on genre/mood
        candidates = random.sample(tracks, min(len(tracks), random.randint(8, 12)))
    elif strategy == 'diversity':
        # Select diverse tracks
        candidates = random.sample(tracks, min(len(tracks), random.randint(10, 15)))
    elif strategy == 'popularity':
        # Select popular tracks (mock popularity score)
        candidates = random.sample(tracks, min(len(tracks), random.randint(6, 10)))
    elif strategy == 'discovery':
        # Select hidden gems
        candidates = random.sample(tracks, min(len(tracks), random.randint(5, 8)))
    else:
        candidates = random.sample(tracks, min(len(tracks), 10))
    
    # Add AI metadata
    for candidate in candidates:
        candidate['ai_selected'] = True
        candidate['selection_reason'] = f'Selected for {strategy} strategy'
        candidate['ai_confidence'] = random.uniform(0.6, 0.9)
    
    return candidates

def refine_playlist_with_ai(playlist, strategy):
    """
    Refine playlist using AI optimization
    Replace with actual AI model
    """
    import random
    
    refined = playlist.copy()
    
    if strategy == 'flow':
        # Optimize for smooth transitions
        random.shuffle(refined)
    elif strategy == 'energy':
        # Create energy curve
        refined.sort(key=lambda x: random.random())
    elif strategy == 'theme':
        # Group by theme/genre
        refined.sort(key=lambda x: x.get('genre', ''))
    elif strategy == 'surprise':
        # Add surprise elements
        random.shuffle(refined)
    
    # Add AI metadata
    for track in refined:
        track['ai_optimized'] = True
        track['optimization_reason'] = f'Optimized for {strategy}'
    
    return refined

def analyze_track_with_ai(track):
    """
    Analyze track with AI for detailed insights
    Replace with actual AI model
    """
    import random
    
    moods = ['energetic', 'chill', 'melancholy', 'aggressive', 'romantic', 'uplifting']
    instruments = ['guitar', 'piano', 'drums', 'bass', 'synth', 'violin', 'saxophone']
    
    mood = random.choice(moods)
    energy = random.uniform(0.1, 1.0)
    mood_score = random.uniform(0.1, 1.0)
    
    analysis = {
        'mood': mood,
        'energy_level': energy,
        'mood_score': mood_score,
        'detected_instruments': random.sample(instruments, random.randint(2, 4)),
        'tempo_bpm': random.randint(60, 180),
        'key_signature': random.choice(['C', 'G', 'D', 'A', 'E', 'F', 'Bb', 'Eb']),
        'time_signature': random.choice(['4/4', '3/4', '6/8']),
        'liner_notes': f"""
        <strong>AI Analysis:</strong><br>
        This {track.get('genre', 'unknown')} track features a {mood} mood with {energy:.1f}/1.0 energy level.
        The composition showcases {', '.join(random.sample(instruments, 3))} creating a distinctive sound.
        Perfect for {random.choice(['building energy', 'creating atmosphere', 'emotional moments', 'dance segments'])} in your playlist.
        <br><br>
        <strong>Musical Elements:</strong><br>
        • Tempo: ~{random.randint(60, 180)} BPM<br>
        • Key: {random.choice(['C', 'G', 'D', 'A'])} Major<br>
        • Style: {track.get('genre', 'Contemporary')}<br>
        • Mood: {mood.title()}<br>
        """,
        'recommendations': [
            'Pairs well with similar tempo tracks',
            f'Great for {mood} playlist sections',
            'Consider for transition moments'
        ]
    }
    
    return analysis


# =====================================================
# END LLAMA AI INTEGRATION
# =====================================================


# Universal search across all connected services
@app.route('/api/streaming/search')
def api_streaming_search():
    """Search across all connected streaming services"""
    query = request.args.get('q', '')
    services = request.args.get('services', 'spotify,soundcloud,youtube,lastfm').split(',')
    
    if not query:
        return jsonify({'error': 'Query parameter required'}), 400
    
    results = {}
    
    for service in services:
        try:
            if service == 'spotify' and load_tokens():
                results['spotify'] = search_spotify(query)
            elif service == 'soundcloud' and load_soundcloud_tokens():
                results['soundcloud'] = search_soundcloud(query)
            elif service == 'youtube' and (YOUTUBE_API_KEY or load_youtube_tokens()):
                results['youtube'] = search_youtube(query)
            elif service == 'lastfm' and LASTFM_API_KEY:
                results['lastfm'] = search_lastfm(query)
        except Exception as e:
            results[service] = {'error': str(e)}
    
    return jsonify({
        'query': query,
        'results': results,
        'searched_services': list(results.keys())
    })

def search_spotify(query):
    """Search Spotify (using existing infrastructure)"""
    # Implementation would use existing Spotify search logic
    return {'placeholder': 'Spotify search results'}

def search_soundcloud(query):
    """Search SoundCloud"""
    tokens = load_soundcloud_tokens()
    if not tokens:
        return {'error': 'Not connected to SoundCloud'}
    
    try:
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        params = {'q': query, 'client_id': SOUNDCLOUD_CLIENT_ID}
        response = requests.get('https://api.soundcloud.com/tracks', headers=headers, params=params)
        
        if response.status_code == 200:
            return {'tracks': response.json()[:10]}  # Limit to 10 results
        else:
            return {'error': 'Search failed'}
    except Exception as e:
        return {'error': str(e)}

def search_youtube(query):
    """Search YouTube Music"""
    if YOUTUBE_API_KEY:
        try:
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'videoCategoryId': '10',  # Music category
                'key': YOUTUBE_API_KEY,
                'maxResults': 10
            }
            response = requests.get('https://www.googleapis.com/youtube/v3/search', params=params)
            
            if response.status_code == 200:
                return {'videos': response.json()}
            else:
                return {'error': 'Search failed'}
        except Exception as e:
            return {'error': str(e)}
    
    return {'error': 'YouTube API key not configured'}

def search_lastfm(query):
    """Search Last.fm"""
    try:
        params = {
            'method': 'track.search',
            'track': query,
            'api_key': LASTFM_API_KEY,
            'format': 'json',
            'limit': 10
        }
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        if response.status_code == 200:
            return {'tracks': response.json()}
        else:
            return {'error': 'Search failed'}
    except Exception as e:
        return {'error': str(e)}


# =====================================================
# END MULTI-STREAMING SERVICE INTEGRATION
# =====================================================


# Startup validation to prevent running with placeholder credentials
def validate_config():
    global STATIC_ONLY
    placeholder_ids = ['your_spotify_client_id_here', 'your_spotify_client_id', 'your_spotify_client_id_here']
    placeholder_secrets = ['your_spotify_client_secret_here', 'your_spotify_client_secret']
    
    # Spotify validation (now permissive for local static serving)
    if not SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_ID.strip() == '':
        print('WARNING: SPOTIFY_CLIENT_ID is not set. Running in static-only mode; Spotify endpoints will be disabled.', file=sys.stderr)
        STATIC_ONLY = True
    elif any(p in SPOTIFY_CLIENT_ID for p in placeholder_ids):
        print('WARNING: SPOTIFY_CLIENT_ID looks like a placeholder. Running in static-only mode.', file=sys.stderr)
        STATIC_ONLY = True
    if not SPOTIFY_CLIENT_SECRET or SPOTIFY_CLIENT_SECRET.strip() == '':
        print('INFO: SPOTIFY_CLIENT_SECRET not set. PKCE-only if enabled later.', file=sys.stderr)
    
    # Optional streaming services validation (warnings only)
    services_status = []
    
    if SOUNDCLOUD_CLIENT_ID:
        services_status.append("✓ SoundCloud configured")
    else:
        services_status.append("⚠ SoundCloud not configured (optional)")
    
    if YOUTUBE_API_KEY or YOUTUBE_CLIENT_ID:
        services_status.append("✓ YouTube Music configured")
    else:
        services_status.append("⚠ YouTube Music not configured (optional)")
    
    if LASTFM_API_KEY:
        services_status.append("✓ Last.fm configured")
    else:
        services_status.append("⚠ Last.fm not configured (optional)")
    
    if PANDORA_CLIENT_ID:
        services_status.append("✓ Pandora configured (requires partnership)")
    else:
        services_status.append("⚠ Pandora not configured (requires partnership)")
    
    if APPLE_MUSIC_KEY_ID and APPLE_MUSIC_TEAM_ID:
        services_status.append("✓ Apple Music configured")
    else:
        services_status.append("⚠ Apple Music not configured (optional)")
    
    print("Streaming Services Status:")
    for status in services_status:
        print(f"  {status}")
    print("")

# Block Spotify endpoints in static-only mode
@app.before_request
def disable_spotify_when_static_only():
    if 'STATIC_ONLY' in globals() and STATIC_ONLY:
        p = request.path
        if p.startswith('/spotify') or p.startswith('/api/spotify'):
            return ('Spotify not configured for this server instance.', 503)

validate_config()

# Will be replaced if ngrok is started
NGROK_URL = None

# Optional: automatically start ngrok to expose local server (requires ngrok installed)
AUTO_NGROK = os.getenv('AUTO_NGROK') in ('1', 'true', 'True')
NGROK_BINARY = os.getenv('NGROK_BINARY', 'ngrok')
NGROK_API = 'http://127.0.0.1:4040/api/tunnels'

def start_ngrok(port, retries=10, wait=0.5):
    global NGROK_URL
    try:
        # Start ngrok in background
        cmd = [NGROK_BINARY, 'http', str(port)]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        app.logger.warning('Failed to start ngrok: %s', e)
        return None

    # Poll ngrok API for public URL
    for _ in range(retries):
        try:
            r = requests.get(NGROK_API, timeout=2)
            if r.ok:
                data = r.json()
                tunnels = data.get('tunnels', [])
                if tunnels:
                    public_url = tunnels[0].get('public_url')
                    if public_url:
                        NGROK_URL = public_url
                        app.logger.info('Ngrok tunnel established: %s', NGROK_URL)
                        return NGROK_URL
        except Exception:
            pass
        time.sleep(wait)
    app.logger.warning('Ngrok did not respond in time')
    return None

def kill_process_on_port(port):
    """Kill any process using the specified port"""
    import signal
    try:
        # Get PIDs using lsof
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            current_pid = os.getpid()
            for pid in pids:
                try:
                    pid_int = int(pid)
                    if pid_int != current_pid:
                        print(f"⚠️  Killing existing process on port {port} (PID: {pid_int})")
                        os.kill(pid_int, signal.SIGKILL)
                except (ValueError, ProcessLookupError):
                    pass
            time.sleep(0.5)  # Give OS time to release port
            return True
    except Exception as e:
        print(f"Note: Could not check port {port}: {e}")
    return False

def run_server(port=8080):
    """Run the Flask server with Spotify integration"""
    
    # Change to the prototype directory
    prototype_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(prototype_dir)
    
    # Kill any existing process on this port
    kill_process_on_port(port)
    
    print(f"\n🚀 iamtoxico Valet Server")
    print(f"📍 http://localhost:{port}")
    print(f"🎭 Valet: http://localhost:{port}/valet.html")
    print(f"\nPress Ctrl+C to stop\n")
    
    # If AUTO_NGROK requested, try to start and obtain public URL
    if AUTO_NGROK:
        app.logger.info('AUTO_NGROK enabled, attempting to start ngrok')
        ngrok_url = start_ngrok(port)
        if ngrok_url:
            # Override REDIRECT_URI for runtime to use the ngrok public URL
            global REDIRECT_URI
            REDIRECT_URI = ngrok_url.rstrip('/') + '/spotify/callback'
            app.logger.info('Using NGROK redirect URI: %s', REDIRECT_URI)

    ssl_context = None
    if SSL_CERT_FILE and SSL_KEY_FILE and os.path.exists(SSL_CERT_FILE) and os.path.exists(SSL_KEY_FILE):
        ssl_context = (SSL_CERT_FILE, SSL_KEY_FILE)
        app.logger.info('Starting HTTPS server with SSL certs')
    else:
        app.logger.info('Starting HTTP server (no SSL certs configured)')

    try:
        app.run(host='0.0.0.0', port=port, debug=False, ssl_context=ssl_context)
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)
    except OSError as e:
        if e.errno == 48 or 'Address already in use' in str(e):  # Address already in use
            print(f"Port {port} is already in use. Trying port {port + 1}")
            run_server(port + 1)
        else:
            raise
    except Exception as e:
        if 'Address already in use' in str(e):
            print(f"Port {port} is already in use. Trying port {port + 1}")
            run_server(port + 1)
        else:
            raise

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
