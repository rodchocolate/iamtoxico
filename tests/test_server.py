"""Tests for the main Flask server (server.py).

Uses the Flask test client. Imports ROOT server.py explicitly via importlib
to avoid name-clash with shopify-app/server.py.
"""
import sys
import os
import json
import time
import importlib.util
import pytest
from unittest.mock import patch, MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _import_main_server():
    """Import the root server.py by absolute file path."""
    spec = importlib.util.spec_from_file_location(
        "main_server", os.path.join(ROOT, "server.py"))
    mod = importlib.util.module_from_spec(spec)
    old_cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        spec.loader.exec_module(mod)
    finally:
        os.chdir(old_cwd)
    return mod


@pytest.fixture(scope="module")
def server_mod():
    os.environ.pop("SPOTIFY_CLIENT_ID", None)
    os.environ.pop("SPOTIFY_CLIENT_SECRET", None)
    return _import_main_server()


@pytest.fixture(scope="module")
def app(server_mod):
    server_mod.app.config["TESTING"] = True
    server_mod.app.config["SECRET_KEY"] = "test-secret"
    return server_mod.app


@pytest.fixture
def client(app):
    return app.test_client()


class TestStaticServing:
    def test_root_returns_index_html(self, client):
        rv = client.get("/")
        assert rv.status_code == 200
        assert b"html" in rv.data.lower() or b"<!DOCTYPE" in rv.data or b"<html" in rv.data

    def test_index_html_serves(self, client):
        rv = client.get("/index.html")
        assert rv.status_code == 200

    def test_landing_html_serves(self, client):
        rv = client.get("/landing.html")
        assert rv.status_code == 200

    def test_shop_html_serves(self, client):
        rv = client.get("/shop.html")
        assert rv.status_code == 200

    def test_styles_css_serves(self, client):
        rv = client.get("/styles.css")
        assert rv.status_code == 200

    def test_nonexistent_file_returns_404(self, client):
        rv = client.get("/does-not-exist.html")
        assert rv.status_code == 404

    def test_favicon_returns_204(self, client):
        rv = client.get("/favicon.ico")
        assert rv.status_code == 204


class TestCatalogAPI:
    def test_catalog_endpoint_returns_json(self, client):
        rv = client.get("/api/valet/catalog")
        assert rv.status_code == 200
        data = rv.get_json()
        assert "products" in data
        assert "count" in data
        assert "meta" in data

    def test_catalog_returns_products(self, client):
        rv = client.get("/api/valet/catalog")
        data = rv.get_json()
        assert data["count"] > 0
        assert len(data["products"]) == data["count"]

    def test_catalog_filter_by_category(self, client):
        rv = client.get("/api/valet/catalog?category=underwear")
        data = rv.get_json()
        for p in data["products"]:
            assert p["category"] == "underwear"

    def test_catalog_filter_by_vibes(self, client):
        rv = client.get("/api/valet/catalog?vibes=bold")
        data = rv.get_json()
        for p in data["products"]:
            assert "bold" in p.get("vibes", [])

    def test_catalog_filter_active_only(self, client):
        rv = client.get("/api/valet/catalog?active_only=true")
        data = rv.get_json()
        for p in data["products"]:
            assert p.get("active", True) is True

    def test_catalog_active_false_returns_all(self, client):
        rv_all = client.get("/api/valet/catalog?active_only=false")
        rv_active = client.get("/api/valet/catalog?active_only=true")
        all_data = rv_all.get_json()
        active_data = rv_active.get_json()
        assert all_data["count"] >= active_data["count"]

    def test_catalog_meta_contains_brand(self, client):
        rv = client.get("/api/valet/catalog")
        data = rv.get_json()
        assert data["meta"]["brand"] == "iamtoxico"

    def test_catalog_returns_activities(self, client):
        rv = client.get("/api/valet/catalog")
        data = rv.get_json()
        assert "activities" in data

    def test_catalog_returns_vibes(self, client):
        rv = client.get("/api/valet/catalog")
        data = rv.get_json()
        assert "vibes" in data

    def test_catalog_filter_multiple_vibes(self, client):
        rv = client.get("/api/valet/catalog?vibes=bold,party")
        data = rv.get_json()
        for p in data["products"]:
            assert "bold" in p.get("vibes", []) or "party" in p.get("vibes", [])


class TestManifestsAPI:
    def test_manifests_endpoint_returns_200(self, client):
        rv = client.get("/api/manifests")
        assert rv.status_code == 200

    def test_manifests_returns_list(self, client):
        rv = client.get("/api/manifests")
        data = rv.get_json()
        assert isinstance(data, list)


class TestSpotifyUnauthenticated:
    """Without Spotify creds the server runs in STATIC_ONLY mode (503)."""

    def test_spotify_status_returns_503_in_static_mode(self, client):
        rv = client.get("/api/spotify/status")
        assert rv.status_code == 503

    def test_spotify_playlists_blocked_in_static_mode(self, client):
        rv = client.get("/api/spotify/playlists")
        assert rv.status_code == 503

    def test_spotify_import_blocked_in_static_mode(self, client):
        rv = client.get("/api/spotify/import")
        assert rv.status_code == 503


class TestServerHelpers:
    def test_token_is_expired_true_when_none(self, server_mod):
        assert server_mod.token_is_expired(None) is True

    def test_token_is_expired_true_when_no_expires_at(self, server_mod):
        assert server_mod.token_is_expired({}) is True

    def test_token_is_expired_true_when_past(self, server_mod):
        assert server_mod.token_is_expired({"expires_at": time.time() - 100}) is True

    def test_token_is_expired_false_when_future(self, server_mod):
        assert server_mod.token_is_expired({"expires_at": time.time() + 3600}) is False

    def test_generate_pkce_pair(self, server_mod):
        verifier, challenge = server_mod.generate_pkce_pair()
        assert len(verifier) > 40
        assert len(challenge) > 20
        assert verifier != challenge

    def test_basic_auth_header_empty_without_secret(self, server_mod):
        original = server_mod.SPOTIFY_CLIENT_SECRET
        server_mod.SPOTIFY_CLIENT_SECRET = None
        try:
            assert server_mod.basic_auth_header() == {}
        finally:
            server_mod.SPOTIFY_CLIENT_SECRET = original

    def test_basic_auth_header_with_secret(self, server_mod):
        original_id = server_mod.SPOTIFY_CLIENT_ID
        original_secret = server_mod.SPOTIFY_CLIENT_SECRET
        server_mod.SPOTIFY_CLIENT_ID = "test-id"
        server_mod.SPOTIFY_CLIENT_SECRET = "test-secret"
        try:
            headers = server_mod.basic_auth_header()
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Basic ")
        finally:
            server_mod.SPOTIFY_CLIENT_ID = original_id
            server_mod.SPOTIFY_CLIENT_SECRET = original_secret
