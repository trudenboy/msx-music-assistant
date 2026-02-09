# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Architecture pivot**: from standalone HA addon to MA Player Provider plugin
- `MSXBridgeProvider` (PlayerProvider) with embedded aiohttp HTTP server
- `MSXPlayer` (Player) with play, pause, stop, volume, and poll support
- MSX interaction plugin (`plugin.html` + `tvx-plugin-module.min.js`) for sidebar menu
- MSX native JSON content pages (albums, artists, playlists, tracks, search)
- MSX detail pages (album tracks, artist albums, playlist tracks)
- MSX search UI with Input Plugin keyboard (`search-page.json`, `search-input.json`)
- Audio playback endpoint (`/msx/audio/{player_id}`) with MA queue integration and PCM→ffmpeg stream encoding
- Stream proxy (`/stream/{player_id}`) for direct audio proxying with same encoding chain
- Content-Length header calculation from track duration and codec bitrate (MP3: 320kbps, AAC: 256kbps) for MSX progress bar support
- Library REST API (`/api/albums`, `/api/artists`, `/api/playlists`, `/api/tracks`, `/api/search`, `/api/recently-played`)
- Playback control API (`/api/play`, `/api/pause`, `/api/stop`, `/api/next`, `/api/previous`)
- Dynamic player registration: TVs register as MA players on-demand via device ID or IP
- Player idle timeout: background task unregisters inactive players (configurable, default 30 min)
- WebSocket push notifications (`/ws`): MA→MSX real-time play/stop events with track metadata
- Device ID detection via `TVXVideoPlugin.requestDeviceId()` with IP fallback
- Multi-TV support: each TV gets a unique player identified by device ID
- Album image fallback: resolves cover from first track when album metadata lacks images
- Status dashboard at root URL (`/`)
- Health endpoint (`/health`)
- CORS middleware for cross-origin MSX requests
- Configurable HTTP port, audio output format, player idle timeout, and stop notification
- `link-to-ma.sh` setup script (venv creation, dependency install, provider symlink)
- `test-server.sh` script for local MA dev server management (start/stop/status/log)
- 58 unit tests (57 passed + 1 skipped) covering provider, player, HTTP server, and setup
- 30 integration tests (require running MA server)

### Fixed
- mypy and ruff formatting synced from ma-server PR
- CI compatibility: remove bundled msx_bridge before symlinking provider

## [1.0.0] - TBD

Initial release.
