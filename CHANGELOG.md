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
- Audio playback endpoint (`/msx/audio/{player_id}`) with MA queue integration and stream proxy
- Stream proxy (`/stream/{player_id}`) for direct audio proxying
- Library REST API (`/api/albums`, `/api/artists`, `/api/playlists`, `/api/tracks`, `/api/search`, `/api/recently-played`)
- Playback control API (`/api/play`, `/api/pause`, `/api/stop`, `/api/next`, `/api/previous`)
- Status dashboard at root URL (`/`)
- Health endpoint (`/health`)
- CORS middleware for cross-origin MSX requests
- Configurable HTTP port and audio output format (mp3/aac/flac)
- `link-to-ma.sh` setup script (venv creation, dependency install, provider symlink)
- 55 unit tests covering provider, player, HTTP server, and setup
- Integration test suite (requires running MA server)

### Deprecated
- `addon/` directory (original standalone HA addon approach, kept for reference)

## [1.0.0] - TBD

Initial release.
