# feat: Add MSX Bridge Player Provider

Adds MSX Bridge Player Provider for streaming music to Smart TVs via Media Station X (MSX) app.

## Features

- MSX bootstrap and native JSON content pages (Albums, Artists, Playlists, Tracks, Search)
- Detail pages for albums, artists, playlists
- Search UI with MSX Input Plugin keyboard
- Audio playback via MSX native player with queue integration and PCM→ffmpeg encoding
- Content-Length header for MSX progress bar (duration * bitrate)
- Stream proxy for programmatic playback
- Dynamic player registration (device ID or IP-based) with idle timeout cleanup
- Multi-TV support: each TV gets its own unique player
- WebSocket push notifications (MA → MSX) for play/stop events
- Library REST API (`/api/albums`, `/api/artists`, `/api/playlists`, `/api/tracks`, `/api/search`, `/api/recently-played`)
- Playback control (play, pause, stop, next, previous)
- 4 config entries: HTTP port, output format, idle timeout, stop notification

## New Files

- `music_assistant/providers/msx_bridge/` — full provider implementation
- No new dependencies (uses aiohttp already in MA)

## Test Coverage

- 58 unit tests (57 passed + 1 skipped)
- 30 integration tests

## Links

- [Media Station X](https://msx.benzac.de/)
- [msx-music-assistant](https://github.com/trudenboy/msx-music-assistant)
