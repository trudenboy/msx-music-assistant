# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant addon that bridges Music Assistant (MA) with Media Station X (MSX) to stream music to smart TVs. The core problem: MSX expects direct HTTP audio URLs, but MA generates ephemeral session-tied "flow" URLs. The bridge addon solves this with a stream proxy, optional transcoding, and a WebSocket relay.

## Architecture

```
Smart TV (MSX App) <--HTTP/WS--> Bridge Addon (Python, port 8099) <--Internal Network--> Music Assistant
```

**Backend** (`addon/bridge/`): Python aiohttp server running in a Docker container as an HA addon.
- `server.py` — `MSXBridgeServer`: main aiohttp app with routes (`/`, `/start.json`, `/msx-plugin.js`, `/stream/{track_uri}`, `/health`, `/ws`)
- `ma_client.py` — `MusicAssistantClient`: WebSocket client to MA API (port 8095)
- `stream_proxy.py` — `StreamProxy`: converts MA flow URLs to direct HTTP streams
- `codec_handler.py` — `CodecHandler`: audio transcoding via ffmpeg (FLAC→MP3, etc.)
- Config is environment-based: `MA_HOST`, `MA_PORT`, `MA_STREAM_PORT`, `ENABLE_TRANSCODING`, `OUTPUT_FORMAT`, `OUTPUT_QUALITY`, `LOG_LEVEL`

**Frontend** (`frontend/`): MSX interaction plugin (TypeScript/JS) served as `/msx-plugin.js`. Directory structure exists but implementation is pending.

**Startup flow**: Docker → `/usr/bin/run.sh` (bashio reads HA config, exports env vars) → `python -m bridge.server`

## Development Commands

### Python Backend (addon)
```bash
# Install dependencies
pip install -r addon/requirements.txt

# Run server locally
cd addon && python -m bridge.server

# Run tests
cd addon && pytest tests/

# Linting & formatting
cd addon && black bridge/
cd addon && pylint bridge/
cd addon && mypy bridge/
```

### Docker
```bash
# Build addon image
docker build -t msx-ma-bridge --build-arg BUILD_FROM=alpine:latest addon/
```

## Code Standards

- **Python**: PEP 8, Black formatting, type hints on all functions
- **Commits**: `type(scope): description` — types: feat, fix, docs, style, refactor, test, chore
- **Async**: All I/O uses async/await (aiohttp, aiofiles, websockets)

## Key Dependencies

| Package | Purpose |
|---------|---------|
| aiohttp | Async HTTP server and client |
| websockets | WebSocket protocol for MA communication |
| mutagen | Audio metadata reading/writing |
| ffmpeg (system) | Audio transcoding |

## Project Status

Early stage — `server.py` is implemented; `ma_client.py`, `stream_proxy.py`, `codec_handler.py` are referenced but not yet created. Frontend is scaffold only. No tests or CI/CD yet.
