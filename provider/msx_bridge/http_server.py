"""Embedded HTTP server for the MSX Bridge Provider."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from aiohttp import ClientSession, web

if TYPE_CHECKING:
    from .provider import MSXBridgeProvider

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


class MSXHTTPServer:
    """HTTP server that serves MSX bootstrap, library API, and stream proxy."""

    def __init__(self, provider: MSXBridgeProvider, port: int) -> None:
        """Initialize the HTTP server."""
        self.provider = provider
        self.port = port
        self.app = web.Application(middlewares=[self._cors_middleware])
        self._runner: web.AppRunner | None = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Register all HTTP routes."""
        # MSX bootstrap
        self.app.router.add_get("/", self._handle_root)
        self.app.router.add_get("/msx/start.json", self._handle_start_json)
        self.app.router.add_get("/msx/plugin.html", self._handle_plugin_html)
        self.app.router.add_get("/msx/tvx-plugin-module.min.js", self._handle_tvx_lib)

        # MSX content pages (native MSX JSON navigation)
        self.app.router.add_get("/msx/menu.json", self._handle_msx_menu)
        self.app.router.add_get("/msx/albums.json", self._handle_msx_albums)
        self.app.router.add_get("/msx/artists.json", self._handle_msx_artists)
        self.app.router.add_get("/msx/playlists.json", self._handle_msx_playlists)
        self.app.router.add_get("/msx/tracks.json", self._handle_msx_tracks)
        self.app.router.add_get("/msx/search.json", self._handle_msx_search)

        # MSX detail pages
        self.app.router.add_get(
            "/msx/albums/{item_id}/tracks.json", self._handle_msx_album_tracks
        )
        self.app.router.add_get(
            "/msx/artists/{item_id}/albums.json", self._handle_msx_artist_albums
        )
        self.app.router.add_get(
            "/msx/playlists/{item_id}/tracks.json", self._handle_msx_playlist_tracks
        )

        # MSX audio playback
        self.app.router.add_get("/msx/audio/{player_id}", self._handle_msx_audio)

        # Health
        self.app.router.add_get("/health", self._handle_health)

        # Stream proxy
        self.app.router.add_get("/stream/{player_id}", self._handle_stream)

        # Library API
        self.app.router.add_get("/api/albums", self._handle_albums)
        self.app.router.add_get(
            "/api/albums/{item_id}/tracks", self._handle_album_tracks
        )
        self.app.router.add_get("/api/artists", self._handle_artists)
        self.app.router.add_get(
            "/api/artists/{item_id}/albums", self._handle_artist_albums
        )
        self.app.router.add_get("/api/playlists", self._handle_playlists)
        self.app.router.add_get(
            "/api/playlists/{item_id}/tracks", self._handle_playlist_tracks
        )
        self.app.router.add_get("/api/tracks", self._handle_tracks)
        self.app.router.add_get("/api/search", self._handle_search)
        self.app.router.add_get("/api/recently-played", self._handle_recently_played)

        # Playback control
        self.app.router.add_post("/api/play", self._handle_play)
        self.app.router.add_post("/api/pause/{player_id}", self._handle_pause)
        self.app.router.add_post("/api/stop/{player_id}", self._handle_stop)
        self.app.router.add_post("/api/next/{player_id}", self._handle_next)
        self.app.router.add_post("/api/previous/{player_id}", self._handle_previous)

    @web.middleware
    async def _cors_middleware(
        self, request: web.Request, handler: Any
    ) -> web.StreamResponse:
        """Add CORS headers to all responses."""
        if request.method == "OPTIONS":
            return web.Response(
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                }
            )
        response = await handler(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    async def start(self) -> None:
        """Start the HTTP server."""
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self.port)
        await site.start()
        logger.info("MSX Bridge HTTP server started on port %s", self.port)

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        logger.info("MSX Bridge HTTP server stopped")

    # --- MSX Bootstrap Routes ---

    async def _handle_root(self, request: web.Request) -> web.Response:
        """Serve status dashboard."""
        players = self.provider.players
        player_info = "".join(
            f"<li>{p.display_name} — {p.playback_state.value}</li>" for p in players
        )
        html = f"""<!DOCTYPE html>
<html>
<head><title>MSX Bridge</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
.info {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 10px 0; }}
code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }}
</style>
</head>
<body>
<h1>MSX Music Assistant Bridge</h1>
<div class="info">
<h3>MSX Setup URL</h3>
<code>http://{request.host}/msx/start.json</code>
</div>
<div class="info">
<h3>Players</h3>
<ul>{player_info or "<li>No players registered</li>"}</ul>
</div>
</body>
</html>"""
        return web.Response(text=html, content_type="text/html")

    async def _handle_start_json(self, request: web.Request) -> web.Response:
        """Return MSX start configuration."""
        host = request.host
        prefix = f"http://{host}"
        start_config = {
            "name": "Music Assistant",
            "version": "1.0.0",
            "parameter": f"menu:request:interaction:init@{prefix}/msx/plugin.html",
        }
        return web.json_response(start_config)

    async def _handle_plugin_html(self, request: web.Request) -> web.Response:
        """Serve the MSX interaction plugin as an HTML page."""
        host = request.host
        prefix = f"http://{host}"
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Music Assistant MSX Plugin</title>
    <script src="{prefix}/msx/tvx-plugin-module.min.js"></script>
</head>
<body>
<script>
(function() {{
    var BRIDGE = "{prefix}";

    function MAHandler() {{}}

    MAHandler.prototype.handleRequest = function(dataId, data, callback) {{
        if (dataId === "init") {{
            callback({{
                name: "Music Assistant",
                version: "1.0.0",
                headline: "Music Assistant",
                menu: [
                    {{ icon: "album", label: "Albums", data: BRIDGE + "/msx/albums.json" }},
                    {{ icon: "person", label: "Artists", data: BRIDGE + "/msx/artists.json" }},
                    {{ icon: "queue-music", label: "Playlists", data: BRIDGE + "/msx/playlists.json" }},
                    {{ icon: "audiotrack", label: "Tracks", data: BRIDGE + "/msx/tracks.json" }}
                ]
            }});
        }}
    }};

    tvx.PluginTools.onReady(function() {{
        tvx.InteractionPlugin.setupHandler(new MAHandler());
        tvx.InteractionPlugin.init();
    }});
}})();
</script>
</body>
</html>"""
        return web.Response(text=html, content_type="text/html")

    async def _handle_tvx_lib(self, request: web.Request) -> web.Response:
        """Serve the TVX plugin module library."""
        lib_path = STATIC_DIR / "tvx-plugin-module.min.js"
        return web.FileResponse(
            lib_path, headers={"Content-Type": "application/javascript"}
        )

    # --- MSX Content Pages (native MSX JSON) ---

    async def _handle_msx_menu(self, request: web.Request) -> web.Response:
        """Return the main library menu as an MSX content page."""
        host = request.host
        prefix = f"http://{host}"
        return web.json_response(
            {
                "type": "list",
                "headline": "Music Assistant",
                "template": {
                    "type": "separate",
                    "layout": "0,0,2,4",
                    "icon": "msx-white-soft:music-note",
                    "action": "content:{context:content}",
                },
                "items": [
                    {
                        "label": "Albums",
                        "icon": "msx-white-soft:album",
                        "content": f"{prefix}/msx/albums.json",
                    },
                    {
                        "label": "Artists",
                        "icon": "msx-white-soft:person",
                        "content": f"{prefix}/msx/artists.json",
                    },
                    {
                        "label": "Playlists",
                        "icon": "msx-white-soft:playlist-play",
                        "content": f"{prefix}/msx/playlists.json",
                    },
                    {
                        "label": "Tracks",
                        "icon": "msx-white-soft:audiotrack",
                        "content": f"{prefix}/msx/tracks.json",
                    },
                ],
            }
        )

    async def _handle_msx_albums(self, request: web.Request) -> web.Response:
        """Return albums as an MSX content page."""
        prefix = f"http://{request.host}"
        limit = int(request.query.get("limit", "50"))
        offset = int(request.query.get("offset", "0"))
        albums = await self.provider.mass.music.albums.library_items(
            limit=limit, offset=offset
        )
        items = []
        for album in albums:
            items.append(
                {
                    "title": album.name,
                    "label": getattr(album, "artist_str", ""),
                    "image": self._get_image_url(album),
                    "action": f"content:{prefix}/msx/albums/{album.item_id}/tracks.json",
                }
            )
        return web.json_response(
            {
                "type": "list",
                "headline": "Albums",
                "template": {
                    "type": "separate",
                    "layout": "0,0,2,4",
                    "imageFiller": "default",
                },
                "items": items if items else [{"title": "No albums found"}],
            }
        )

    async def _handle_msx_artists(self, request: web.Request) -> web.Response:
        """Return artists as an MSX content page."""
        prefix = f"http://{request.host}"
        limit = int(request.query.get("limit", "50"))
        offset = int(request.query.get("offset", "0"))
        artists = await self.provider.mass.music.artists.library_items(
            limit=limit, offset=offset
        )
        items = []
        for artist in artists:
            items.append(
                {
                    "title": artist.name,
                    "image": self._get_image_url(artist),
                    "action": f"content:{prefix}/msx/artists/{artist.item_id}/albums.json",
                }
            )
        return web.json_response(
            {
                "type": "list",
                "headline": "Artists",
                "template": {
                    "type": "separate",
                    "layout": "0,0,2,4",
                    "icon": "msx-white-soft:person",
                    "imageFiller": "default",
                },
                "items": items if items else [{"title": "No artists found"}],
            }
        )

    async def _handle_msx_playlists(self, request: web.Request) -> web.Response:
        """Return playlists as an MSX content page."""
        prefix = f"http://{request.host}"
        limit = int(request.query.get("limit", "50"))
        offset = int(request.query.get("offset", "0"))
        playlists = await self.provider.mass.music.playlists.library_items(
            limit=limit, offset=offset
        )
        items = []
        for playlist in playlists:
            items.append(
                {
                    "title": playlist.name,
                    "image": self._get_image_url(playlist),
                    "action": f"content:{prefix}/msx/playlists/{playlist.item_id}/tracks.json",
                }
            )
        return web.json_response(
            {
                "type": "list",
                "headline": "Playlists",
                "template": {
                    "type": "separate",
                    "layout": "0,0,2,4",
                    "icon": "msx-white-soft:playlist-play",
                    "imageFiller": "default",
                },
                "items": items if items else [{"title": "No playlists found"}],
            }
        )

    async def _handle_msx_tracks(self, request: web.Request) -> web.Response:
        """Return tracks as an MSX content page."""
        prefix = f"http://{request.host}"
        limit = int(request.query.get("limit", "50"))
        offset = int(request.query.get("offset", "0"))
        tracks = await self.provider.mass.music.tracks.library_items(
            limit=limit, offset=offset
        )
        items = [self._format_msx_track(track, prefix) for track in tracks]
        return web.json_response(
            {
                "type": "list",
                "headline": "Tracks",
                "template": {
                    "type": "separate",
                    "layout": "0,0,2,4",
                    "icon": "msx-white-soft:audiotrack",
                    "imageFiller": "default",
                },
                "items": items if items else [{"title": "No tracks found"}],
            }
        )

    async def _handle_msx_search(self, request: web.Request) -> web.Response:
        """Return search results as an MSX content page."""
        prefix = f"http://{request.host}"
        query = request.query.get("q", "")
        if not query:
            return web.json_response(
                {
                    "type": "list",
                    "headline": "Search",
                    "items": [{"title": "Please enter a search query"}],
                }
            )
        limit = int(request.query.get("limit", "20"))
        results = await self.provider.mass.music.search(query, limit=limit)
        items = []
        for artist in results.artists:
            items.append(
                {
                    "title": artist.name,
                    "label": "Artist",
                    "icon": "msx-white-soft:person",
                    "image": self._get_image_url(artist),
                    "action": f"content:{prefix}/msx/artists/{artist.item_id}/albums.json",
                }
            )
        for album in results.albums:
            items.append(
                {
                    "title": album.name,
                    "label": f"Album — {getattr(album, 'artist_str', '')}",
                    "icon": "msx-white-soft:album",
                    "image": self._get_image_url(album),
                    "action": f"content:{prefix}/msx/albums/{album.item_id}/tracks.json",
                }
            )
        for track in results.tracks:
            item = self._format_msx_track(track, prefix)
            item["label"] = f"Track — {getattr(track, 'artist_str', '')}"
            item["icon"] = "msx-white-soft:audiotrack"
            items.append(item)
        return web.json_response(
            {
                "type": "list",
                "headline": f"Search: {query}",
                "template": {
                    "type": "separate",
                    "layout": "0,0,2,4",
                    "imageFiller": "default",
                },
                "items": items if items else [{"title": "No results found"}],
            }
        )

    # --- MSX Detail Pages ---

    async def _handle_msx_album_tracks(self, request: web.Request) -> web.Response:
        """Return tracks for an album as an MSX content page."""
        prefix = f"http://{request.host}"
        item_id = request.match_info["item_id"]
        try:
            tracks = await self.provider.mass.music.albums.tracks(item_id, "library")
        except Exception:
            logger.warning("Failed to fetch tracks for album %s", item_id)
            tracks = []
        items = [self._format_msx_track(track, prefix) for track in tracks]
        return web.json_response(
            {
                "type": "list",
                "headline": "Album Tracks",
                "template": {
                    "type": "separate",
                    "layout": "0,0,2,4",
                    "icon": "msx-white-soft:audiotrack",
                    "imageFiller": "default",
                },
                "items": items if items else [{"title": "No tracks found"}],
            }
        )

    async def _handle_msx_artist_albums(self, request: web.Request) -> web.Response:
        """Return albums for an artist as an MSX content page."""
        prefix = f"http://{request.host}"
        item_id = request.match_info["item_id"]
        try:
            albums = await self.provider.mass.music.artists.albums(item_id, "library")
        except Exception:
            logger.warning("Failed to fetch albums for artist %s", item_id)
            albums = []
        items = []
        for album in albums:
            items.append(
                {
                    "title": album.name,
                    "label": getattr(album, "artist_str", ""),
                    "image": self._get_image_url(album),
                    "action": f"content:{prefix}/msx/albums/{album.item_id}/tracks.json",
                }
            )
        return web.json_response(
            {
                "type": "list",
                "headline": "Artist Albums",
                "template": {
                    "type": "separate",
                    "layout": "0,0,2,4",
                    "imageFiller": "default",
                },
                "items": items if items else [{"title": "No albums found"}],
            }
        )

    async def _handle_msx_playlist_tracks(self, request: web.Request) -> web.Response:
        """Return tracks for a playlist as an MSX content page."""
        prefix = f"http://{request.host}"
        item_id = request.match_info["item_id"]
        try:
            tracks = [
                t
                async for t in self.provider.mass.music.playlists.tracks(
                    item_id, "library"
                )
            ]
        except Exception:
            logger.warning("Failed to fetch tracks for playlist %s", item_id)
            tracks = []
        items = [self._format_msx_track(track, prefix) for track in tracks]
        return web.json_response(
            {
                "type": "list",
                "headline": "Playlist Tracks",
                "template": {
                    "type": "separate",
                    "layout": "0,0,2,4",
                    "icon": "msx-white-soft:audiotrack",
                    "imageFiller": "default",
                },
                "items": items if items else [{"title": "No tracks found"}],
            }
        )

    # --- MSX Audio Playback ---

    async def _handle_msx_audio(self, request: web.Request) -> web.StreamResponse:
        """Trigger playback via MA queue and proxy the audio stream."""
        player_id = request.match_info["player_id"]
        uri = request.query.get("uri")
        if not uri:
            return web.Response(status=400, text="Missing uri parameter")

        player = self.provider.mass.players.get(player_id)
        if not player:
            return web.Response(status=404, text="Player not found")

        from .player import MSXPlayer

        if not isinstance(player, MSXPlayer):
            return web.Response(status=400, text="Not an MSX player")

        # Trigger playback through MA queue system
        await self.provider.mass.player_queues.play_media(player_id, uri)

        # Wait for stream URL to be set (play_media is async internally)
        stream_url = None
        for _ in range(100):  # Poll up to 10 seconds
            stream_url = player.current_stream_url
            if stream_url:
                break
            await asyncio.sleep(0.1)

        if not stream_url:
            return web.Response(status=504, text="Playback setup timeout")

        # Proxy audio stream (same logic as _handle_stream)
        output_format = player.output_format
        content_types = {
            "mp3": "audio/mpeg",
            "aac": "audio/aac",
            "flac": "audio/flac",
        }
        content_type = content_types.get(output_format, "audio/mpeg")

        response = web.StreamResponse(
            status=200,
            headers={"Content-Type": content_type, "Cache-Control": "no-cache"},
        )
        await response.prepare(request)

        try:
            async with ClientSession() as session:
                async with session.get(stream_url) as upstream:
                    async for chunk in upstream.content.iter_chunked(8192):
                        await response.write(chunk)
        except ConnectionResetError:
            logger.debug("Client disconnected from audio stream %s", player_id)
        except Exception:
            logger.exception("Audio stream proxy error for player %s", player_id)

        return response

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response(
            {
                "status": "ok",
                "provider": "msx_bridge",
                "players": len(self.provider.players),
            }
        )

    # --- Stream Proxy ---

    async def _handle_stream(self, request: web.Request) -> web.StreamResponse:
        """Proxy audio stream from MA to the TV."""
        player_id = request.match_info["player_id"]
        player = self.provider.mass.players.get(player_id)
        if not player:
            return web.Response(status=404, text="Player not found")

        from .player import MSXPlayer

        if not isinstance(player, MSXPlayer):
            return web.Response(status=400, text="Not an MSX player")

        stream_url = player.current_stream_url
        if not stream_url:
            return web.Response(status=404, text="No active stream")

        # Determine content type from output format
        output_format = player.output_format
        content_types = {
            "mp3": "audio/mpeg",
            "aac": "audio/aac",
            "flac": "audio/flac",
        }
        content_type = content_types.get(output_format, "audio/mpeg")

        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": content_type,
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        await response.prepare(request)

        # Proxy the audio stream from MA
        try:
            async with ClientSession() as session:
                async with session.get(stream_url) as upstream:
                    async for chunk in upstream.content.iter_chunked(8192):
                        await response.write(chunk)
        except ConnectionResetError:
            logger.debug("Client disconnected from stream %s", player_id)
        except Exception:
            logger.exception("Stream proxy error for player %s", player_id)

        return response

    # --- Library API Routes ---

    async def _handle_albums(self, request: web.Request) -> web.Response:
        """List albums."""
        limit = int(request.query.get("limit", "50"))
        offset = int(request.query.get("offset", "0"))
        albums = await self.provider.mass.music.albums.library_items(
            limit=limit, offset=offset
        )
        return web.json_response(
            {
                "items": [
                    {
                        "item_id": str(album.item_id),
                        "name": album.name,
                        "artist": getattr(album, "artist_str", ""),
                        "image": self._get_image_url(album),
                        "uri": album.uri,
                    }
                    for album in albums
                ],
                "total": albums.total if hasattr(albums, "total") else len(albums),
            }
        )

    async def _handle_album_tracks(self, request: web.Request) -> web.Response:
        """List tracks for an album."""
        item_id = request.match_info["item_id"]
        tracks = await self.provider.mass.music.albums.tracks(item_id, "library")
        return web.json_response(
            {
                "items": [self._format_track(track) for track in tracks],
            }
        )

    async def _handle_artists(self, request: web.Request) -> web.Response:
        """List artists."""
        limit = int(request.query.get("limit", "50"))
        offset = int(request.query.get("offset", "0"))
        artists = await self.provider.mass.music.artists.library_items(
            limit=limit, offset=offset
        )
        return web.json_response(
            {
                "items": [
                    {
                        "item_id": str(artist.item_id),
                        "name": artist.name,
                        "image": self._get_image_url(artist),
                        "uri": artist.uri,
                    }
                    for artist in artists
                ],
                "total": artists.total if hasattr(artists, "total") else len(artists),
            }
        )

    async def _handle_artist_albums(self, request: web.Request) -> web.Response:
        """List albums for an artist."""
        item_id = request.match_info["item_id"]
        albums = await self.provider.mass.music.artists.albums(item_id, "library")
        return web.json_response(
            {
                "items": [
                    {
                        "item_id": str(album.item_id),
                        "name": album.name,
                        "artist": getattr(album, "artist_str", ""),
                        "image": self._get_image_url(album),
                        "uri": album.uri,
                    }
                    for album in albums
                ],
            }
        )

    async def _handle_playlists(self, request: web.Request) -> web.Response:
        """List playlists."""
        limit = int(request.query.get("limit", "50"))
        offset = int(request.query.get("offset", "0"))
        playlists = await self.provider.mass.music.playlists.library_items(
            limit=limit, offset=offset
        )
        return web.json_response(
            {
                "items": [
                    {
                        "item_id": str(playlist.item_id),
                        "name": playlist.name,
                        "image": self._get_image_url(playlist),
                        "uri": playlist.uri,
                    }
                    for playlist in playlists
                ],
                "total": playlists.total
                if hasattr(playlists, "total")
                else len(playlists),
            }
        )

    async def _handle_playlist_tracks(self, request: web.Request) -> web.Response:
        """List tracks for a playlist."""
        item_id = request.match_info["item_id"]
        tracks = [
            t
            async for t in self.provider.mass.music.playlists.tracks(item_id, "library")
        ]
        return web.json_response(
            {
                "items": [self._format_track(track) for track in tracks],
            }
        )

    async def _handle_tracks(self, request: web.Request) -> web.Response:
        """List tracks."""
        limit = int(request.query.get("limit", "50"))
        offset = int(request.query.get("offset", "0"))
        tracks = await self.provider.mass.music.tracks.library_items(
            limit=limit, offset=offset
        )
        return web.json_response(
            {
                "items": [self._format_track(track) for track in tracks],
                "total": tracks.total if hasattr(tracks, "total") else len(tracks),
            }
        )

    async def _handle_search(self, request: web.Request) -> web.Response:
        """Search the music library."""
        query = request.query.get("q", "")
        if not query:
            return web.json_response(
                {"error": "Missing query parameter 'q'"}, status=400
            )
        limit = int(request.query.get("limit", "20"))
        results = await self.provider.mass.music.search(query, limit=limit)
        return web.json_response(
            {
                "artists": [
                    {
                        "item_id": str(a.item_id),
                        "name": a.name,
                        "image": self._get_image_url(a),
                        "uri": a.uri,
                    }
                    for a in results.artists
                ],
                "albums": [
                    {
                        "item_id": str(a.item_id),
                        "name": a.name,
                        "artist": getattr(a, "artist_str", ""),
                        "image": self._get_image_url(a),
                        "uri": a.uri,
                    }
                    for a in results.albums
                ],
                "tracks": [self._format_track(t) for t in results.tracks],
                "playlists": [
                    {
                        "item_id": str(p.item_id),
                        "name": p.name,
                        "image": self._get_image_url(p),
                        "uri": p.uri,
                    }
                    for p in results.playlists
                ],
            }
        )

    async def _handle_recently_played(self, request: web.Request) -> web.Response:
        """Return recently played items."""
        limit = int(request.query.get("limit", "20"))
        tracks = await self.provider.mass.music.tracks.library_items(
            limit=limit, order_by="last_played"
        )
        return web.json_response(
            {
                "items": [self._format_track(track) for track in tracks],
            }
        )

    # --- Playback Control Routes ---

    async def _handle_play(self, request: web.Request) -> web.Response:
        """Start playback of a track."""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        track_uri = body.get("track_uri")
        player_id = body.get("player_id")
        if not track_uri or not player_id:
            return web.json_response(
                {"error": "Missing track_uri or player_id"}, status=400
            )

        await self.provider.mass.player_queues.play_media(player_id, track_uri)
        return web.json_response({"status": "ok"})

    async def _handle_pause(self, request: web.Request) -> web.Response:
        """Pause playback."""
        player_id = request.match_info["player_id"]
        await self.provider.mass.players.cmd_pause(player_id)
        return web.json_response({"status": "ok"})

    async def _handle_stop(self, request: web.Request) -> web.Response:
        """Stop playback."""
        player_id = request.match_info["player_id"]
        await self.provider.mass.players.cmd_stop(player_id)
        return web.json_response({"status": "ok"})

    async def _handle_next(self, request: web.Request) -> web.Response:
        """Skip to next track."""
        player_id = request.match_info["player_id"]
        await self.provider.mass.players.cmd_next_track(player_id)
        return web.json_response({"status": "ok"})

    async def _handle_previous(self, request: web.Request) -> web.Response:
        """Skip to previous track."""
        player_id = request.match_info["player_id"]
        await self.provider.mass.players.cmd_previous_track(player_id)
        return web.json_response({"status": "ok"})

    # --- Helpers ---

    def _format_track(self, track: Any) -> dict:
        """Format a track object for the API response."""
        return {
            "item_id": str(track.item_id),
            "name": track.name,
            "artist": getattr(track, "artist_str", ""),
            "album": getattr(getattr(track, "album", None), "name", ""),
            "duration": getattr(track, "duration", 0),
            "image": self._get_image_url(track),
            "uri": track.uri,
        }

    def _format_msx_track(self, track: Any, prefix: str) -> dict:
        """Format a track as an MSX content item with playback action."""
        return {
            "title": track.name,
            "label": getattr(track, "artist_str", ""),
            "playerLabel": track.name,
            "image": self._get_image_url(track),
            "action": f"audio:{prefix}/msx/audio/msx_default?uri={quote(track.uri, safe='')}",
        }

    def _get_image_url(self, item: Any) -> str | None:
        """Get an image URL for a media item."""
        if hasattr(item, "image") and item.image:
            return self.provider.mass.metadata.get_image_url(item.image)
        return None
