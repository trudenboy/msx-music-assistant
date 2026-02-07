"""Integration tests for the MSX Bridge Provider.

These tests start a real MusicAssistant server, load the msx_bridge provider
via save_provider_config(), and verify end-to-end behaviour.
"""

from __future__ import annotations

import aiohttp
import pytest
from music_assistant_models.enums import PlaybackState, PlayerFeature, PlayerType

from music_assistant.mass import MusicAssistant
from music_assistant.models.player import PlayerMedia
from music_assistant.providers.msx_bridge.player import MSXPlayer

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Group 1: Provider lifecycle
# ---------------------------------------------------------------------------


async def test_provider_discovered_by_manifest(mass: MusicAssistant) -> None:
    """msx_bridge manifest is present and has type=player."""
    manifests = mass.get_provider_manifests()
    domains = {m.domain for m in manifests}
    assert "msx_bridge" in domains

    manifest = mass.get_provider_manifest("msx_bridge")
    assert manifest.type.value == "player"


async def test_provider_loads_successfully(mass: MusicAssistant, msx_provider) -> None:
    """Provider is loaded and available after save_provider_config."""
    provider = mass.get_provider("msx_bridge")
    assert provider is not None
    assert provider.available


async def test_provider_unload_cleans_up(mass: MusicAssistant, msx_port: int) -> None:
    """After removal: provider gone, player gone, port freed."""
    from tests.integration.conftest import _wait_for_player

    config = await mass.config.save_provider_config(
        "msx_bridge",
        {"http_port": msx_port, "output_format": "mp3"},
    )
    await _wait_for_player(mass, "msx_default")

    # Verify provider is up
    assert mass.get_provider("msx_bridge") is not None

    # Remove
    await mass.config.remove_provider_config(config.instance_id)

    # Provider should be gone
    assert mass.get_provider("msx_bridge") is None

    # Player should be gone
    assert mass.players.get("msx_default") is None

    # Port should be free (connection refused)
    with pytest.raises(aiohttp.ClientConnectorError):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{msx_port}/health"):
                pass


# ---------------------------------------------------------------------------
# Group 2: Player registration
# ---------------------------------------------------------------------------


async def test_default_player_registered(mass: MusicAssistant, msx_provider) -> None:
    """Default player is registered with expected attributes."""
    player = mass.players.get("msx_default")
    assert player is not None
    assert player.player_id == "msx_default"
    assert player.type == PlayerType.PLAYER
    assert PlayerFeature.PAUSE in player.supported_features
    assert PlayerFeature.VOLUME_SET in player.supported_features


async def test_player_initial_state(mass: MusicAssistant, msx_provider) -> None:
    """Player starts in IDLE with volume 100."""
    player = mass.players.get("msx_default")
    assert player is not None
    assert player.playback_state == PlaybackState.IDLE
    assert player.volume_level == 100


async def test_player_is_msx_player_subclass(
    mass: MusicAssistant, msx_provider
) -> None:
    """Player is an MSXPlayer with expected custom attributes."""
    player = mass.players.get("msx_default")
    assert isinstance(player, MSXPlayer)
    assert player.current_stream_url is None
    assert player.output_format == "mp3"


# ---------------------------------------------------------------------------
# Group 3: HTTP server accessibility
# ---------------------------------------------------------------------------


async def test_http_health(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /health returns 200 with status ok and player count."""
    resp = await msx_http_client.get("/health")
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    assert data["players"] >= 1


async def test_http_start_json(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /msx/start.json returns interaction mode config with plugin.html."""
    resp = await msx_http_client.get("/msx/start.json")
    assert resp.status == 200
    data = await resp.json()
    assert data["name"] == "Music Assistant"
    assert "menu:request:interaction:init@" in data["parameter"]
    assert "plugin.html" in data["parameter"]
    assert "scripts" not in data


async def test_http_plugin_html(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /msx/plugin.html returns HTML with interaction plugin."""
    resp = await msx_http_client.get("/msx/plugin.html")
    assert resp.status == 200
    assert "text/html" in resp.content_type
    text = await resp.text()
    assert "tvx.InteractionPlugin" in text
    assert "handleRequest" in text


async def test_http_root_dashboard(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET / returns an HTML dashboard containing 'MSX'."""
    resp = await msx_http_client.get("/")
    assert resp.status == 200
    assert "text/html" in resp.content_type
    text = await resp.text()
    assert "MSX" in text


async def test_http_cors_headers(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """Responses include Access-Control-Allow-Origin: *."""
    resp = await msx_http_client.get("/health")
    assert resp.headers.get("Access-Control-Allow-Origin") == "*"


# ---------------------------------------------------------------------------
# Group 4: Library API — empty library
# ---------------------------------------------------------------------------


async def test_api_albums_empty(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /api/albums returns 200 with empty items."""
    resp = await msx_http_client.get("/api/albums")
    assert resp.status == 200
    data = await resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_api_artists_empty(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /api/artists returns 200 with empty items."""
    resp = await msx_http_client.get("/api/artists")
    assert resp.status == 200
    data = await resp.json()
    assert data["items"] == []


async def test_api_playlists_empty(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /api/playlists returns 200 with empty items."""
    resp = await msx_http_client.get("/api/playlists")
    assert resp.status == 200
    data = await resp.json()
    assert data["items"] == []


async def test_api_tracks_empty(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /api/tracks returns 200 with empty items."""
    resp = await msx_http_client.get("/api/tracks")
    assert resp.status == 200
    data = await resp.json()
    assert data["items"] == []


async def test_api_search_empty(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /api/search?q=test returns empty lists; missing q returns 400."""
    resp = await msx_http_client.get("/api/search?q=test")
    assert resp.status == 200
    data = await resp.json()
    assert data["artists"] == []
    assert data["albums"] == []
    assert data["tracks"] == []
    assert data["playlists"] == []

    # Missing query parameter
    resp_bad = await msx_http_client.get("/api/search")
    assert resp_bad.status == 400


# ---------------------------------------------------------------------------
# Group 5: Playback via Player API
# ---------------------------------------------------------------------------


async def test_play_media_stores_stream_url(mass: MusicAssistant, msx_provider) -> None:
    """play_media() stores the stream URL and sets state to PLAYING."""
    player = mass.players.get("msx_default")
    assert isinstance(player, MSXPlayer)

    await player.play_media(PlayerMedia(uri="http://example.com/stream.mp3"))

    assert player.current_stream_url == "http://example.com/stream.mp3"
    assert player.playback_state == PlaybackState.PLAYING


async def test_stop_clears_stream_url(mass: MusicAssistant, msx_provider) -> None:
    """stop() clears stream URL and sets state to IDLE."""
    player = mass.players.get("msx_default")
    assert isinstance(player, MSXPlayer)

    await player.play_media(PlayerMedia(uri="http://example.com/stream.mp3"))
    assert player.playback_state == PlaybackState.PLAYING

    await player.stop()
    assert player.current_stream_url is None
    assert player.playback_state == PlaybackState.IDLE


# ---------------------------------------------------------------------------
# Group 6: Stream proxy — error cases
# ---------------------------------------------------------------------------


async def test_stream_no_active_stream(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /stream/msx_default without play_media returns 404."""
    resp = await msx_http_client.get("/stream/msx_default")
    assert resp.status == 404
    text = await resp.text()
    assert "No active stream" in text


async def test_stream_unknown_player(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /stream/nonexistent returns 404 Player not found."""
    resp = await msx_http_client.get("/stream/nonexistent")
    assert resp.status == 404
    text = await resp.text()
    assert "Player not found" in text


# ---------------------------------------------------------------------------
# Group 7: Playback control via HTTP
# ---------------------------------------------------------------------------


async def test_pause_via_http(
    mass: MusicAssistant,
    msx_provider,
    msx_http_client: aiohttp.ClientSession,
) -> None:
    """POST /api/pause/msx_default pauses the player."""
    player = mass.players.get("msx_default")
    assert isinstance(player, MSXPlayer)

    # Start playback first
    await player.play_media(PlayerMedia(uri="http://example.com/stream.mp3"))
    assert player.playback_state == PlaybackState.PLAYING

    resp = await msx_http_client.post("/api/pause/msx_default")
    assert resp.status == 200
    assert player.playback_state == PlaybackState.PAUSED


async def test_stop_via_http(
    mass: MusicAssistant,
    msx_provider,
    msx_http_client: aiohttp.ClientSession,
) -> None:
    """POST /api/stop/msx_default stops the player."""
    player = mass.players.get("msx_default")
    assert isinstance(player, MSXPlayer)

    # Start playback first
    await player.play_media(PlayerMedia(uri="http://example.com/stream.mp3"))
    assert player.playback_state == PlaybackState.PLAYING

    resp = await msx_http_client.post("/api/stop/msx_default")
    assert resp.status == 200
    assert player.playback_state == PlaybackState.IDLE


async def test_play_invalid_body_via_http(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """POST /api/play with invalid JSON or missing fields returns 400."""
    # Invalid JSON
    resp = await msx_http_client.post(
        "/api/play", data=b"not-json", headers={"Content-Type": "application/json"}
    )
    assert resp.status == 400

    # Missing required fields
    resp2 = await msx_http_client.post("/api/play", json={})
    assert resp2.status == 400


# ---------------------------------------------------------------------------
# Group 8: MSX content page actions
# ---------------------------------------------------------------------------


async def test_msx_albums_empty_has_fallback(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /msx/albums.json with empty library returns fallback item."""
    resp = await msx_http_client.get("/msx/albums.json")
    assert resp.status == 200
    data = await resp.json()
    assert data["type"] == "list"
    assert data["headline"] == "Albums"
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "No albums found"


async def test_msx_tracks_empty_has_fallback(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /msx/tracks.json with empty library returns fallback item."""
    resp = await msx_http_client.get("/msx/tracks.json")
    assert resp.status == 200
    data = await resp.json()
    assert data["type"] == "list"
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "No tracks found"


async def test_msx_audio_missing_uri(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /msx/audio/msx_default without ?uri= returns 400."""
    resp = await msx_http_client.get("/msx/audio/msx_default")
    assert resp.status == 400
    text = await resp.text()
    assert "Missing uri" in text


async def test_msx_audio_unknown_player(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /msx/audio/nonexistent?uri=x returns 404."""
    resp = await msx_http_client.get("/msx/audio/nonexistent?uri=library://track/1")
    assert resp.status == 404
    text = await resp.text()
    assert "Player not found" in text


async def test_msx_detail_album_tracks_empty(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /msx/albums/999/tracks.json with no tracks returns fallback."""
    resp = await msx_http_client.get("/msx/albums/999/tracks.json")
    assert resp.status == 200
    data = await resp.json()
    assert data["headline"] == "Album Tracks"
    assert data["items"][0]["title"] == "No tracks found"


async def test_msx_detail_artist_albums_empty(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /msx/artists/999/albums.json with no albums returns fallback."""
    resp = await msx_http_client.get("/msx/artists/999/albums.json")
    assert resp.status == 200
    data = await resp.json()
    assert data["headline"] == "Artist Albums"
    assert data["items"][0]["title"] == "No albums found"


async def test_msx_detail_playlist_tracks_empty(
    mass: MusicAssistant, msx_http_client: aiohttp.ClientSession
) -> None:
    """GET /msx/playlists/999/tracks.json with no tracks returns fallback."""
    resp = await msx_http_client.get("/msx/playlists/999/tracks.json")
    assert resp.status == 200
    data = await resp.json()
    assert data["headline"] == "Playlist Tracks"
    assert data["items"][0]["title"] == "No tracks found"
