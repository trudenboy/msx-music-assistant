# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Music Assistant (MA) Player Provider that streams music to Smart TVs via the Media Station X (MSX) app. Implemented as an MA provider plugin — runs inside the MA server process with direct access to internal APIs.

## Architecture

```
Smart TV (MSX App) --HTTP--> MSXBridgeProvider (inside MA, port 8099) --internal API--> MA core
```

**Provider** (`provider/msx_bridge/`): MA Player Provider with embedded HTTP server.
- `__init__.py` — `setup()`, `get_config_entries()`, provider entry point
- `provider.py` — `MSXBridgeProvider(PlayerProvider)`: manages lifecycle, registers players, starts HTTP server
- `player.py` — `MSXPlayer(Player)`: represents a Smart TV as an MA player. Stores stream URL from `play_media()` for the TV to fetch via HTTP.
- `http_server.py` — `MSXHTTPServer`: aiohttp server with routes for MSX bootstrap, library browsing, playback control, and stream proxy
- `constants.py` — config keys and defaults
- `manifest.json` — provider metadata for MA

**Legacy addon** (`addon/`): Original standalone bridge approach (deprecated, kept for reference).

**Frontend** (`frontend/`): MSX TypeScript plugin (scaffolding, not yet active). The provider currently serves an inline JS interaction plugin via `plugin.html`.

### Key Flows

**MSX Bootstrap & Navigation:**
1. TV loads `/msx/start.json` → points to `/msx/plugin.html` as interaction plugin
2. Plugin returns menu items (Albums, Artists, Playlists, Tracks) → MSX renders sidebar
3. Clicking a menu item loads a content page (e.g. `/msx/albums.json`) → MSX renders list
4. Content items have `action: "content:..."` (drill to detail page) or `action: "audio:..."` (play track)

**Audio Playback (via MSX native player):**
1. Track item has `action: "audio:/msx/audio/{player_id}?uri=<track_uri>"`
2. `GET /msx/audio/{player_id}?uri=...` → calls `mass.player_queues.play_media()` to enqueue
3. Polls `MSXPlayer.current_stream_url` (up to 10s) until MA sets the stream URL
4. Proxies audio bytes from MA stream URL → TV speakers

**Direct Stream Proxy (for programmatic playback):**
1. MA calls `play_media(media)` on `MSXPlayer` → player stores `media.uri` as `current_stream_url`
2. TV fetches `GET /stream/{player_id}` → HTTP server proxies audio from `current_stream_url`

**Library REST API:**
- TV or external client calls `/api/albums`, `/api/artists`, etc. → server calls `mass.music.*` internally

## Development Setup

```bash
# Clone MA server fork alongside this project (if not already done)
cd /Users/renso/Projects && git clone https://github.com/trudenboy/ma-server.git

# Setup venv, install deps, symlink provider — one command does it all
./scripts/link-to-ma.sh
```

### Working with the MA venv

All commands (server, tests, pre-commit, linting) must run inside the MA venv:

```bash
# Activate the venv
source /Users/renso/Projects/ma-server/.venv/bin/activate

# Start MA server (provider auto-loads)
cd /Users/renso/Projects/ma-server && python -m music_assistant --log-level debug

# Run tests
cd /Users/renso/Projects/ma-server && pytest

# Pre-commit (linting, formatting)
cd /Users/renso/Projects/ma-server && pre-commit run --all-files

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
- Player registration and state management (play, pause, stop, volume, poll)
- MSX bootstrap (`/msx/start.json`, `/msx/plugin.html`, `/msx/tvx-plugin-module.min.js`)
- MSX native JSON content pages with `action` fields (`/msx/albums.json`, `/msx/artists.json`, `/msx/playlists.json`, `/msx/tracks.json`, `/msx/search.json`)
- MSX detail pages (`/msx/albums/{id}/tracks.json`, `/msx/artists/{id}/albums.json`, `/msx/playlists/{id}/tracks.json`)
- Audio playback endpoint (`/msx/audio/{player_id}?uri=...`) with queue integration and stream proxy
- Stream proxy (`/stream/{player_id}`)
- Library REST API (`/api/albums`, `/api/artists`, `/api/playlists`, `/api/tracks`, `/api/search`, `/api/recently-played`)
- Playback control (`/api/play`, `/api/pause`, `/api/stop`, `/api/next`, `/api/previous`)
- Health endpoint (`/health`)
- Status dashboard (`/`)
- 55 unit tests + integration test suite
- `_format_msx_track()` helper reused across tracks, album tracks, playlist tracks, and search

Next steps: integration testing with real MA server + MSX app, multi-TV support, full MSX TypeScript plugin.
