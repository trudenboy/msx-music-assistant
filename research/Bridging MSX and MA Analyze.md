# Bridging MSX and Music Assistant: a feasibility analysis

**Building an MSX plugin for Music Assistant is technically feasible but requires a middleware proxy server** to bridge two fundamentally different streaming architectures. MSX expects direct HTTP audio URLs (like `audio:https://example.com/track.mp3`), while Music Assistant generates ephemeral, session-bound "flow" stream URLs tied to registered players. This mismatch is the central engineering challenge. The good news: a proven integration pattern exists — the Alexa bridge for MA demonstrates that flow URLs are playable by external HTTP clients — and both projects expose the APIs needed to make this work. The middleware would use MA's REST/WebSocket API for library browsing and search, then proxy MA's audio streams to MSX-compatible URLs.

## How MSX's plugin architecture works

Media Station X is a cross-platform smart TV application (Samsung Tizen, LG webOS, Android TV, Fire TV, Apple TV, Xbox, and web browsers) that acts as a rendering shell for third-party content. Developers define menus, content grids, and media actions through JSON data structures, and MSX renders them with a TV-optimized UI. The framework supports three integration approaches, two of which are relevant here.

**The server-side service pattern** is what SoundCloud MSX uses. A backend server (PHP, Node.js, Python — any language) generates MSX-compatible JSON dynamically. MSX fetches a `start.json` file containing a parameter like `menu:user:http://yourserver/msx/service`, which returns a Menu Root Object — a JSON structure defining navigation items. Each menu item's `data` property points to a URL returning a Content Root Object, which contains an array of content items laid out on MSX's **12×6 grid system**. Each item can have a title, artist text, artwork image, and an `action` property that triggers playback:

```json
{
  "title": "Track Name",
  "titleFooter": "Artist Name", 
  "image": "https://server/cover.jpg",
  "playerLabel": "Track Name - Artist Name",
  "action": "audio:https://server/stream/track-123.mp3"
}
```

**The interaction plugin pattern** is more powerful. A TypeScript/JavaScript application runs inside an iframe, communicating with MSX via the `TVXInteractionPlugin` API. It can dynamically generate menus, handle search input, manage authentication, and make arbitrary API calls. The open-source RBTV MSX project on GitHub demonstrates this pattern with full source code. For audio playback, MSX natively supports MP3, FLAC, WAV, and OGG via HTML5 audio, plus HLS and DASH streaming through bundled player plugins (hls.js, dash.js, Shaka Player). The `audio:{URL}` action plays any direct HTTP audio URL, displaying album art as a background while providing built-in transport controls.

Both patterns require CORS headers (`Access-Control-Allow-Origin: *`) on the serving backend. Search is supported through MSX's Input Plugin, which captures keyboard input and appends it to a configurable URL. Playlist playback works via item grouping and sequential navigation.

## Music Assistant exposes a rich but streaming-constrained API

Music Assistant runs as a Python asyncio server (aiohttp-based) with **two HTTP servers**: a webserver on **port 8095** serving the frontend, WebSocket API, and REST API, plus a stream server on **port 8097** delivering audio to players. The API is accessible through both a WebSocket endpoint at `ws://<ip>:8095/ws` and a REST endpoint at `POST http://<ip>:8095/api`, using identical JSON message formats:

```json
{
  "message_id": "1",
  "command": "music/search",
  "args": {"search_query": "Beatles", "media_types": ["track", "album"], "limit": 25}
}
```

The library browsing API is comprehensive. Commands include `music/search` for cross-provider search, `music/item_by_uri` for retrieving item details, `music/albums/album_tracks` for album contents, `music/playlists/playlist_tracks` for playlists, and `music/recently_played_items` for history. Items use a URI scheme like `library://track/42` or `spotify://track/1234`. Auto-generated API documentation is available at `http://<ip>:8095/api-docs` since v2.7.0. Authentication uses token-based auth (required since schema version 28), with long-lived tokens creatable through the web UI.

**The critical limitation is audio streaming.** MA does not expose a `get_stream_url(track_id)` command. Instead, it uses a proxy-transcoding architecture: audio from any provider (Spotify, local files, Tidal, etc.) is decoded to raw PCM via ffmpeg, processed (volume normalization, EQ), and re-encoded to FLAC or MP3 for delivery. Stream URLs follow the pattern `http://<ip>:8097/flow/<queue_id>/<player_name>/<uuid>.flac` — they are **ephemeral, session-specific, and tied to a registered player queue**. As lead developer Marcel Veldt confirmed: "Music Assistant generates unique stream URLs on the fly for each playback session."

## The SoundCloud MSX showcase reveals the ideal integration pattern

SoundCloud MSX (hosted at `sc.msx.benzac.de`, version 1.0.14) is a closed-source PHP service that serves as the canonical example of music streaming integration with MSX. Its architecture is straightforward: the PHP backend calls SoundCloud's API using a `client_id`, transforms responses into MSX JSON, and embeds direct stream URLs as `audio:{url}` actions. The MSX client never touches the SoundCloud API directly.

The flow is: `start.json` → Menu Root Object (Charts, Search, Genres) → Content Root Objects (track listings with artwork and stream URLs) → `audio:{stream_url}` playback. This works because **SoundCloud provides stable, direct HTTP stream URLs** for public tracks. The entire integration is stateless — each JSON response contains all the information MSX needs.

Replicating this pattern for Music Assistant requires solving the streaming URL problem. Where SoundCloud gives you `https://api.soundcloud.com/tracks/123/stream?client_id=xxx`, Music Assistant gives you nothing until a player is registered and playback is commanded through its queue system.

## A middleware proxy makes the integration viable

The most architecturally sound approach is a **middleware server** (Python recommended, given MA's ecosystem) that bridges both APIs. This middleware would serve two roles: an MSX-compatible JSON API for browsing and navigation, and a stream proxy that mediates between MA's player system and MSX's expectation of direct audio URLs. Here is the proposed architecture:

**For library browsing**, the middleware translates MSX requests into MA API calls. When MSX fetches a menu, the middleware calls `music/search` or `music/albums/album_tracks` via MA's REST API, transforms the response into MSX Content Root Objects, and returns JSON with proper artwork URLs and navigation structure. This part is straightforward — MA's browsing API maps cleanly to MSX's content model (tracks → content items with title, artist, image, action).

**For audio streaming**, three viable approaches exist, ranked by practicality:

The **stream proxy approach** is most promising. The middleware registers a virtual player with MA (using the player provider API or the BuiltinPlayer mechanism), commands playback via `player_queues/play_media`, captures the resulting flow URL, and proxies the audio stream to MSX under a stable URL like `http://middleware:8080/stream/track-123.flac`. MSX sees a normal HTTP audio URL. The Alexa bridge project (`timlaing/music-assistant-alexa-api`) proves this pattern works — users confirmed flow URLs play fine in VLC and web browsers.

The **MPD relay approach** uses MPD (Music Player Daemon) as an intermediary. MA plays to MPD, which exposes a fixed HTTP stream at `http://host:8000/`. MSX plays that single stream URL. This is simpler but loses per-track control — MSX becomes a remote control for a single stream rather than a full browsing experience.

The **interaction plugin approach** leverages MSX's most powerful plugin type. A TypeScript interaction plugin running in MSX's iframe context could connect directly to MA's WebSocket API, register as a BuiltinPlayer, and use the Web Audio API or HTML5 Audio element for playback. This eliminates the middleware server but is constrained by smart TV browser capabilities (WebSocket support varies, and some TV platforms restrict iframe network access).

## Technical challenges and architecture considerations

**Stream lifecycle management** is the hardest problem. MA's flow URLs are continuous streams — track transitions happen within the same HTTP connection, not as separate URLs. The middleware must either break the flow stream into per-track segments (complex, requires understanding MA's stream protocol) or maintain a persistent connection to MA and re-serve audio chunks to MSX on demand. MSX's built-in audio player expects discrete URLs per track, so the middleware needs to handle this translation.

**Seeking is server-side only.** MA's stream server does not support HTTP range requests because it often cannot determine file sizes upfront (especially for transcoded or streaming-provider content). MSX's native player may attempt range-based seeking, which would fail. The middleware would need to intercept seek requests and translate them into MA's server-side seeking mechanism, or the MSX plugin would need to use a custom Audio Plugin that handles seeking through MA's API.

**CORS and network topology** present practical challenges. MA's stream server (port 8097) runs HTTP-only on the local network. If the MSX client runs on a smart TV on the same LAN, direct access works. For remote access, the middleware must proxy streams. The middleware itself must serve CORS headers for MSX compatibility. MA's webserver API (port 8095) may need CORS configuration for direct browser access from an interaction plugin.

**Authentication adds complexity** in recent MA versions (v2.7+). The middleware needs to store and refresh MA access tokens. If using the interaction plugin approach, token management must happen in-browser JavaScript — secure storage on smart TV platforms is limited.

**Platform variability** across MSX's target devices (Samsung Tizen, LG webOS, Android TV) means audio codec support differs. MA defaults to FLAC output, but some TV platforms handle MP3 more reliably. The middleware should request MP3 encoding from MA for maximum compatibility, accepting the quality tradeoff, or detect the platform and adjust.

## Recommended implementation roadmap

The highest-confidence path is a **Python middleware using the server-side service pattern**, similar to SoundCloud MSX but with a stream proxy layer. The implementation would have four components:

The **MSX JSON service** (Flask or aiohttp) serves `start.json`, menu endpoints, and content endpoints. It calls MA's REST API for library data and transforms responses into MSX JSON. This is the simplest component — a few hundred lines mapping MA's data model (artists, albums, tracks, playlists) to MSX's content item structure.

The **stream proxy** maintains a persistent connection to MA's API, registers a virtual player, and when MSX requests audio for a specific track, commands MA to play it and captures the flow URL. It then serves the audio stream at a predictable URL that MSX can consume via `audio:http://middleware:8080/stream/{track_uri}.mp3`.

The **search handler** accepts MSX Input Plugin search queries, forwards them to MA's `music/search` command, and returns results as MSX content items. MA's search is cross-provider (Spotify, local files, Tidal simultaneously), which would give MSX users a unified search across all configured music sources.

The **image proxy** (optional but recommended) routes album art through the middleware to avoid CORS issues with MA's image proxy or provider CDNs. MA already proxies images through its webserver, so the middleware can forward those URLs.

## Conclusion

This integration is **feasible with moderate engineering effort** — roughly comparable to building the Alexa bridge that already exists for MA. The browsing/search side maps cleanly between the two APIs. The streaming side requires the most work but has proven precedents. The key insight is that **MA's flow URLs are standard HTTP audio streams once generated** — the challenge is only in obtaining them, not in playing them. An MSX interaction plugin combined with a lightweight Python middleware represents the most flexible architecture, giving MSX users full browse, search, and playback access to MA's 30+ music providers through a TV-optimized interface. The RBTV MSX open-source codebase (TypeScript interaction plugin) and the Alexa bridge (Python stream URL capture) together provide concrete reference implementations for both halves of the problem.