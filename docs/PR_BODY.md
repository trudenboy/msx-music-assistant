# feat: Add MSX Bridge Player Provider

Adds MSX Bridge Player Provider for streaming music to Smart TVs via Media Station X (MSX) app.

## Features

- MSX bootstrap and native JSON content pages (Albums, Artists, Playlists, Tracks, Search)
- Detail pages for albums, artists, playlists
- Audio playback via MSX native player with queue integration
- Stream proxy for programmatic playback
- Library REST API (`/api/albums`, `/api/artists`, `/api/playlists`, `/api/tracks`, `/api/search`)
- Playback control (play, pause, stop, next, previous)

## New Files

- `music_assistant/providers/msx_bridge/` — full provider implementation
- No new dependencies (uses aiohttp already in MA)

## Links

- [Media Station X](https://msx.benzac.de/)
- [msx-music-assistant](https://github.com/trudenboy/msx-music-assistant)
