# MSX Music Assistant Bridge

Stream your [Music Assistant](https://music-assistant.io/) library to Smart TVs through [Media Station X](https://msx.benzac.de/) with a native TV-optimized interface.

## Features

- **MA Player Provider** — runs inside the Music Assistant server process, no separate containers or addons
- **MSX Native UI** — browse albums, artists, playlists, and tracks with remote-control-friendly navigation
- **Library Browsing** — drill into album tracks, artist albums, playlist tracks, and search results
- **Audio Playback** — stream audio to the TV through MA's queue system with automatic stream proxy
- **Universal TV Support** — works on any TV/device running the MSX app (Samsung Tizen, LG webOS, Android TV, Fire TV, Apple TV, web browsers)
- **Configurable Output** — MP3, AAC, or FLAC output format
- **Local Network** — runs entirely on your LAN, no cloud dependencies

## Architecture

```
┌─────────────┐         ┌───────────────────────────────────────┐
│  Smart TV   │         │        Music Assistant Server          │
│  (MSX App)  │  HTTP   │  ┌─────────────────────────────────┐  │
│             │ ◄─────► │  │   MSXBridgeProvider (port 8099) │  │
│ - JSON nav  │         │  │   ├── MSXHTTPServer (aiohttp)   │  │
│ - Audio     │         │  │   └── MSXPlayer                 │  │
│ - Plugin    │         │  └───────────┬──────────────────────┘  │
└─────────────┘         │              │ internal API             │
                        │  ┌───────────▼──────────────────────┐  │
                        │  │        MA Core                    │  │
                        │  │  music, players, player_queues    │  │
                        │  └───────────────────────────────────┘  │
                        └───────────────────────────────────────┘
```

### Components

| Component | Class | Role |
|-----------|-------|------|
| **Provider** | `MSXBridgeProvider` | MA `PlayerProvider` — manages lifecycle, registers players, starts HTTP server |
| **Player** | `MSXPlayer` | MA `Player` — represents a Smart TV. Stores stream URL from `play_media()` for the TV to fetch |
| **HTTP Server** | `MSXHTTPServer` | aiohttp server — serves MSX bootstrap, content pages, audio proxy, and REST API |

### MSX Navigation Flow

```
start.json ──► plugin.html (interaction plugin)
                    │
                    ▼
               Main Menu
            ┌────┬────┬────┐
            ▼    ▼    ▼    ▼
         Albums Artists Playlists Tracks
            │    │       │         │
            ▼    ▼       ▼         ▼
         Album  Artist  Playlist  ► Play
         Tracks Albums  Tracks
            │    │       │
            ▼    ▼       ▼
          ► Play ► Drill ► Play
```

Content pages return MSX JSON with `action` fields:
- `"content:..."` — drill down to a detail page
- `"audio:..."` — start audio playback

### Audio Playback Flow

```
TV clicks track
    │
    ▼
GET /msx/audio/{player_id}?uri=<track_uri>
    │
    ├─► play_media() enqueues track via MA queue system
    ├─► poll MSXPlayer.current_stream_url (up to 10s)
    └─► proxy audio bytes from MA stream URL → TV speakers
```

## Quick Start

### Prerequisites

- [Music Assistant](https://music-assistant.io/) server (or a fork of the [MA server repo](https://github.com/trudenboy/ma-server))
- [Media Station X](https://msx.benzac.de/) app on your Smart TV
- Python 3.12+

### Setup

```bash
# 1. Clone this repo alongside the MA server
cd ~/Projects
git clone https://github.com/trudenboy/msx-music-assistant.git
git clone https://github.com/trudenboy/ma-server.git  # if not already

# 2. Setup venv, install deps, symlink provider into MA
cd msx-music-assistant
./scripts/link-to-ma.sh

# 3. Start MA server (provider auto-loads)
source ../ma-server/.venv/bin/activate
cd ../ma-server && python -m music_assistant --log-level debug
```

### Configure your TV

1. Open the MSX app on your Smart TV
2. Go to **Settings > Start Parameter**
3. Enter: `http://<YOUR_SERVER_IP>:8099/msx/start.json`
4. Restart MSX

You can also visit `http://<YOUR_SERVER_IP>:8099/` in a browser for a status dashboard showing the setup URL and registered players.

## HTTP Endpoints

### MSX Bootstrap

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Status dashboard (HTML) |
| GET | `/msx/start.json` | MSX start configuration |
| GET | `/msx/plugin.html` | MSX interaction plugin (HTML/JS) |
| GET | `/msx/tvx-plugin-module.min.js` | TVX plugin library |

### MSX Content Pages (native JSON navigation)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/msx/menu.json` | Main library menu |
| GET | `/msx/albums.json` | Albums list with drill-down actions |
| GET | `/msx/artists.json` | Artists list with drill-down actions |
| GET | `/msx/playlists.json` | Playlists list with drill-down actions |
| GET | `/msx/tracks.json` | Tracks list with play actions |
| GET | `/msx/search.json?q=...` | Search results (artists, albums, tracks) |

### MSX Detail Pages

| Method | Path | Description |
|--------|------|-------------|
| GET | `/msx/albums/{id}/tracks.json` | Tracks for an album |
| GET | `/msx/artists/{id}/albums.json` | Albums for an artist |
| GET | `/msx/playlists/{id}/tracks.json` | Tracks for a playlist |

### Audio & Stream

| Method | Path | Description |
|--------|------|-------------|
| GET | `/msx/audio/{player_id}?uri=...` | Trigger playback via MA queue + proxy audio stream |
| GET | `/stream/{player_id}` | Direct stream proxy (for already-playing media) |

### REST API (JSON)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/albums` | List albums |
| GET | `/api/albums/{id}/tracks` | Album tracks |
| GET | `/api/artists` | List artists |
| GET | `/api/artists/{id}/albums` | Artist albums |
| GET | `/api/playlists` | List playlists |
| GET | `/api/playlists/{id}/tracks` | Playlist tracks |
| GET | `/api/tracks` | List tracks |
| GET | `/api/search?q=...` | Search library |
| GET | `/api/recently-played` | Recently played tracks |

### Playback Control

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/play` | Start playback (`{track_uri, player_id}`) |
| POST | `/api/pause/{player_id}` | Pause |
| POST | `/api/stop/{player_id}` | Stop |
| POST | `/api/next/{player_id}` | Next track |
| POST | `/api/previous/{player_id}` | Previous track |

### Utility

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (`{status, provider, players}`) |

## Configuration

The provider exposes two config entries in the MA UI:

| Key | Default | Description |
|-----|---------|-------------|
| `http_port` | `8099` | Port for the embedded HTTP server |
| `output_format` | `mp3` | Audio format for streaming (`mp3`, `aac`, `flac`) |

## Development

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (used by MA for venv management)
- MA server fork cloned alongside this project

### Setup & Run

```bash
# One-command setup: creates venv, installs deps, symlinks provider
./scripts/link-to-ma.sh

# Activate venv (required for all commands)
source /Users/renso/Projects/ma-server/.venv/bin/activate

# Start server
cd /Users/renso/Projects/ma-server && python -m music_assistant --log-level debug

# Run tests
pytest tests/ -v --ignore=tests/integration

# Run linting
cd /Users/renso/Projects/ma-server && pre-commit run --all-files

# Verify provider imports
python -c "from music_assistant.providers.msx_bridge import setup; print('OK')"
```

See [CLAUDE.md](CLAUDE.md) for detailed development guidance and MA conventions.

## Project Structure

```
provider/msx_bridge/
├── __init__.py        # setup(), get_config_entries() — provider entry point
├── provider.py        # MSXBridgeProvider(PlayerProvider) — lifecycle, player registration
├── player.py          # MSXPlayer(Player) — Smart TV as MA player
├── http_server.py     # MSXHTTPServer — aiohttp routes for MSX + API
├── constants.py       # Config keys and defaults
├── manifest.json      # Provider metadata for MA
└── static/
    └── tvx-plugin-module.min.js  # TVX plugin library

tests/
├── conftest.py        # Shared fixtures (mock MA, players, HTTP server)
├── test_init.py       # Provider setup tests
├── test_player.py     # MSXPlayer unit tests
├── test_provider.py   # MSXBridgeProvider unit tests
├── test_http_server.py # HTTP route tests
└── integration/       # Integration tests (require running MA server)

scripts/
└── link-to-ma.sh      # Setup venv + symlink provider into MA server

addon/                 # Legacy standalone HA addon (deprecated)
frontend/              # MSX TypeScript plugin (scaffolding, not yet active)
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE).

## Credits

- [Music Assistant](https://music-assistant.io/) by Marcel Veldt
- [Media Station X](https://msx.benzac.de/) by Benjamin Zachey

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
