# Plan: Browser SPA + Sendspin-js (Deferred)

Saved from analysis session. Return to this when ready to add browser support.

## Concept

```
Smart TV (MSX App)  → JSON content pages → MSX native player → HTTP audio proxy (current)
Browser SPA         → Custom HTML UI     → sendspin-js       → WebSocket audio (MA native)
Both share          → Same REST API (/api/*)
```

## Key Discovery: Sendspin JS

`@music-assistant/sendspin-js` is MA's native browser audio player:
- Connects to MA via **WebSocket** (port 8927) — MA server already runs this
- MA **pushes** audio over WebSocket (FLAC/Opus binary chunks)
- Uses **Web Audio API** for playback (not HTML5 `<audio>`)
- Browser auto-registers as an MA player on connect
- Full playback control: play, pause, stop, volume, skip, seek
- Multi-room synchronized playback for free
- **MA's own web frontend already uses sendspin-js** — this is the proven approach
- npm: `@music-assistant/sendspin-js`, source: https://github.com/Sendspin/sendspin-js

## Why Sendspin for browser but not MSX?

| | MSX TV | Browser SPA |
|---|---|---|
| **Audio delivery** | HTTP stream (`audio:` action) | WebSocket (sendspin-js) |
| **Player registration** | MSXPlayer (our code) | Auto via sendspin-js |
| **UI rendering** | MSX native JSON | Custom HTML/JS |
| **Playback control** | MSX built-in controls | sendspin-js API |

MSX has its own native media player that expects HTTP URLs via `audio:` actions. Sendspin-js uses Web Audio API which doesn't integrate with MSX's player.

## Files to Create

| File | Purpose |
|---|---|
| `provider/msx_bridge/static/app.html` | Browser SPA entry point |
| `provider/msx_bridge/static/app.js` | SPA: router, components, API client |
| `provider/msx_bridge/static/app.css` | SPA styles (dark theme, responsive) |
| `provider/msx_bridge/static/sendspin.js` | Bundled sendspin-js (or load from MA server) |

## Files to Modify

| File | Change |
|---|---|
| `provider/msx_bridge/http_server.py` | Add routes: `GET /app` → app.html, CSS/JS assets |

## SPA Features (MVP)

1. **Library browsing** — Albums, Artists, Playlists, Tracks grids with cover art
2. **Search** — Text input → `/api/search` → instant results
3. **Detail pages** — Album tracks, Artist albums, Playlist tracks
4. **Audio playback** — sendspin-js connects to MA, browser becomes a player
5. **Now playing bar** — Current track, play/pause, skip, volume, progress
6. **Responsive** — Desktop + mobile browsers

## Sendspin Integration Example

```javascript
// 1. Connect to MA's Sendspin server
const player = new SendspinPlayer({
  playerId: 'msx-browser-' + generateId(),
  serverUrl: `ws://${location.hostname}:8927/sendspin`,
  clientName: 'MSX Browser Player',
});
await player.connect();

// 2. Browse library via REST API
const albums = await fetch('/api/albums').then(r => r.json());

// 3. Play a track — tell MA to play on this sendspin player
await fetch('/api/play', {
  method: 'POST',
  body: JSON.stringify({ track_uri: 'library://track/123', player_id: player.playerId })
});
// MA pushes audio to browser via sendspin WebSocket automatically
```

## Open Questions

1. **Sendspin-js distribution**: Bundle from npm, or load from MA server's existing frontend assets?
2. **Auth**: Does the WebSocket proxy at `/sendspin` on MA's main port (8095) require auth? If so, can we use the unauthenticated direct port (8927)?
3. **Player ID persistence**: Should browser player ID be stored in localStorage for session continuity?

## Effort Estimate

~2-3K LOC (UI only, audio handled by sendspin-js). ~15-20 files. Vanilla JS, no framework.
