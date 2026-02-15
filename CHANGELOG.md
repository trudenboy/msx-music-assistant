# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Group Stream Modes** — new `group_stream_mode` config option: `independent` (default, each TV gets own ffmpeg process) or `shared` (one ffmpeg, multiple readers — less CPU usage)
- **Sendspin Plugin Infrastructure** — `sendspin-plugin.html` TVX Video Plugin with sync indicator UI (disabled by default, reserved for future MA Sendspin integration)
- **Remove Player** — `ProviderFeature.REMOVE_PLAYER` enabled, allowing deletion of MSX players from MA UI
- **Recently Played** — `/msx/recently-played.json` content page and `/msx/playlist/recently-played.json` playlist endpoint
- **Web Player Enhancements** — Sendspin mode infrastructure in web player (disabled), kiosk mode URL param `?kiosk=1`
- **Instant Stop** — `notify_play_stopped` sends broadcast_stop + cancel_streams twice (same as Disable) so Stop in MA closes MSX immediately
- **Pause → stop on MSX** — Pause calls `notify_play_stopped` to close the MSX player; Play calls `mass.player_queues.resume()` to re-send the current track
- **Quick stop** — `POST /api/quick-stop/{player_id}` and dashboard button for direct HTTP control
- **on_player_disabled** override — keeps player registered on Disable so it reappears on Enable; still broadcasts stop for instant MSX close
- **Config option** `abort_stream_first` — abort stream before broadcast_stop (may help on some TVs)
- **MSX plugin** — uses `[player:eject|player:hide]` chain when `showNotification=false`
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
