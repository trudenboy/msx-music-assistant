# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Music Assistant (MA) Player Provider that streams music to Smart TVs via the Media Station X (MSX) app. Implemented as an MA provider plugin — runs inside the MA server process with direct access to internal APIs.

## Architecture

```
Smart TV (MSX App) --HTTP--> MSXBridgeProvider (inside MA, port 8099) --internal API--> MA core
```

**Provider** (`provider/msx_bridge/`): MA Player Provider with embedded HTTP server.
- `__init__.py` — `setup()`, `get_config_entries()` (7 config entries), provider entry point
- `provider.py` — `MSXBridgeProvider(PlayerProvider)`: manages lifecycle, dynamic player registration, idle timeout loop, WebSocket push notifications, starts HTTP server
- `player.py` — `MSXPlayer(Player)`: represents a Smart TV as an MA player. Stores stream URL from `play_media()` for the TV to fetch via HTTP.
- `http_server.py` — `MSXHTTPServer`: aiohttp server with routes for MSX bootstrap, library browsing, playback control, WebSocket, and stream proxy
- `constants.py` — config keys and defaults (7 config entries: `http_port`, `output_format`, `player_idle_timeout`, `show_stop_notification`, `abort_stream_first`, `enable_player_grouping`, `group_stream_mode`)
- `manifest.json` — provider metadata for MA
- `static/` — static files served by aiohttp:
  - `plugin.html` — MSX interaction plugin (detects device ID, opens WebSocket, builds menu)
  - `sendspin-plugin.html` — Sendspin TVX Video Plugin (reserved for future use)
  - `input.html` — MSX Input Plugin wrapper (search keyboard)
  - `input.js` — Input Plugin logic
  - `tvx-plugin-module.min.js` — TVX plugin module library
  - `tvx-plugin.min.js` — TVX plugin library
  - `web/` — Browser-based web player (index.html, web.js)

### Key Flows

**MSX Bootstrap & Navigation:**
1. TV loads `/msx/start.json` → points to `/msx/plugin.html` as interaction plugin
2. Plugin detects device ID via `TVXVideoPlugin.requestDeviceId()` (falls back to IP)
3. Plugin opens WebSocket to `/ws?device_id=...` for push playback notifications
4. Plugin requests `/msx/menu.json?device_id=...` → returns menu items (Search, Albums, Artists, Playlists, Tracks)
5. Clicking a menu item loads a content page (e.g. `/msx/albums.json?device_id=...`) → MSX renders list
6. All URLs carry `device_id` param so the server maps requests to the correct player
7. Content items have `action: "content:..."` (drill to detail page) or `action: "audio:..."` (play track)

**Dynamic Player Registration:**
1. Any MSX request calls `_ensure_player_for_request()` → extracts `device_id` or IP → derives `player_id`
2. `provider.get_or_register_player(player_id)` creates an `MSXPlayer` on-demand if not already registered
3. Background idle timeout loop runs every 60s → unregisters players with no activity for `player_idle_timeout` minutes (default: 30)
4. Handles race conditions via `_pending_unregisters` events

**Audio Playback (via MSX native player):**
1. Track item has `action: "audio:/msx/audio/{player_id}?uri=<track_uri>&device_id=..."`
2. `GET /msx/audio/{player_id}?uri=...` → resolves track metadata for duration, then calls `mass.player_queues.play_media()` to enqueue
3. Polls `MSXPlayer.current_media` (up to 10s) until MA sets the PlayerMedia
4. Streams audio: `mass.streams.get_stream()` → raw PCM → `get_ffmpeg_stream()` → encoded MP3/AAC/FLAC → TV
5. Sets `Content-Length` header from `duration * bitrate` (MP3: 40,000 B/s, AAC: 32,000 B/s) — required for MSX progress bar

**WebSocket Push (MA → MSX):**
1. Plugin connects to `/ws?device_id=...` on startup
2. When MA calls `play_media()` on `MSXPlayer`, player calls `notify_play_started()` → broadcasts `{type: "play", path, title, artist, image_url, duration}` to subscribed WebSocket clients
3. When MA calls `stop()` or `pause()`, `notify_play_stopped()` broadcasts `{type: "stop", showNotification}` (sent twice for instant MSX close)
4. Plugin receives messages and calls `executeAction("[player:eject|player:hide]")` or `"eject"`
5. **Resume:** When `play()` is called from PAUSED, `MSXPlayer.play()` calls `mass.player_queues.resume(player_id)` → queue re-sends current track to MSX

**Direct Stream Proxy (for programmatic playback):**
1. MA calls `play_media(media)` on `MSXPlayer` → player stores `media.uri` as `current_stream_url`
2. TV fetches `GET /stream/{player_id}` → HTTP server streams audio via PCM → ffmpeg → encoded output

**Library REST API:**
- TV or external client calls `/api/albums`, `/api/artists`, etc. → server calls `mass.music.*` internally

## Development Setup

```bash
# Clone MA server fork alongside this project (if not already done)
cd .. && git clone https://github.com/trudenboy/ma-server.git

# Setup venv, install deps, symlink provider — one command does it all
./scripts/link-to-ma.sh
```

### Working with the MA venv

All commands (server, tests, pre-commit, linting) must run inside the MA venv:

```bash
# Activate the venv
source ../ma-server/.venv/bin/activate

# Start MA server (provider auto-loads)
cd ../ma-server && python -m music_assistant --log-level debug

# Run tests
cd ../ma-server && pytest

# Pre-commit (linting, formatting)
cd ../ma-server && pre-commit run --all-files

# Verify provider imports
python -c "from music_assistant.providers.msx_bridge import setup; print('OK')"
```

## Code Standards

- **Python**: PEP 8, type hints on all functions, `from __future__ import annotations`
- **Commits**: `type(scope): description` — types: feat, fix, docs, style, refactor, test, chore
- **Async**: All I/O uses async/await (aiohttp)
- **MA conventions**: Follow patterns from `_demo_player_provider` and `sendspin` providers

## Key Files Reference (MA Server)

| Path | Purpose |
|------|---------|
| `music_assistant/models/player.py` | `Player` base class |
| `music_assistant/models/player_provider.py` | `PlayerProvider` base class |
| `music_assistant/providers/_demo_player_provider/` | Template provider |
| `music_assistant/providers/sendspin/` | Reference: provider with embedded HTTP server |

## Project Status

`MSXBridgeProvider`, `MSXPlayer`, and `MSXHTTPServer` are implemented with:
- Dynamic player registration (device ID or IP-based) with idle timeout cleanup
- Multi-TV support (each TV gets its own player via device ID)
- WebSocket push notifications (MA → MSX for play/stop events)
- Player state management (play, pause, stop, volume, poll)
- MSX bootstrap (`/msx/start.json`, `/msx/plugin.html`, static assets)
- MSX interaction plugin with device ID detection and WebSocket client
- MSX native JSON content pages with `action` fields (`/msx/menu.json`, `/msx/albums.json`, `/msx/artists.json`, `/msx/playlists.json`, `/msx/tracks.json`, `/msx/search.json`, `/msx/search-page.json`, `/msx/search-input.json`)
- MSX detail pages (`/msx/albums/{id}/tracks.json`, `/msx/artists/{id}/albums.json`, `/msx/playlists/{id}/tracks.json`)
- Audio playback endpoint (`/msx/audio/{player_id}?uri=...`) with queue integration, PCM→ffmpeg encoding, and Content-Length for progress bar
- Stream proxy (`/stream/{player_id}`) with same PCM→ffmpeg encoding chain
- Library REST API (`/api/albums`, `/api/artists`, `/api/playlists`, `/api/tracks`, `/api/search`, `/api/recently-played`)
- Playback control (`/api/play`, `/api/pause`, `/api/stop`, `/api/quick-stop/{player_id}`, `/api/next`, `/api/previous`)
- Health endpoint (`/health`)
- Status dashboard (`/`)
- 58 unit tests (57 passed + 1 skipped) + 30 integration tests
- `_format_msx_track()` helper reused across tracks, album tracks, playlist tracks, and search
- 7 config entries: `http_port`, `output_format`, `player_idle_timeout`, `show_stop_notification`, `abort_stream_first`, `enable_player_grouping`, `group_stream_mode`
- Browser web player (`/web`) with library browsing, playback controls, and keyboard shortcuts
- Group stream modes: Independent (separate ffmpeg per TV) or Shared Buffer (one ffmpeg, multiple readers)
- Sendspin plugin infrastructure (disabled, reserved for future MA Sendspin integration)
- `on_player_disabled` override: does not unregister (player stays on Enable); still broadcasts stop for instant MSX close

Next steps: integration testing with real MA server + MSX app, full MSX TypeScript plugin.
