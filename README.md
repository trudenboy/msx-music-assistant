# MSX Music Assistant Integration

<p align="center">
  <img src="docs/images/logo.png" alt="MSX-MA Logo" width="200"/>
</p>

<p align="center">
  <a href="https://github.com/your-username/msx-music-assistant/releases">
    <img src="https://img.shields.io/github/v/release/your-username/msx-music-assistant" alt="Release">
  </a>
  <a href="https://github.com/your-username/msx-music-assistant/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/your-username/msx-music-assistant/build-addon.yml" alt="Build">
  </a>
  <a href="https://github.com/your-username/msx-music-assistant/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/your-username/msx-music-assistant" alt="License">
  </a>
</p>

Stream your entire Music Assistant library to Smart TVs through Media Station X with a native TV-optimized interface.

## Features

✨ **Universal Smart TV Support** - Works on Samsung Tizen, LG webOS, Android TV, Fire TV, Apple TV, and web browsers  
🎵 **Full Library Access** - Browse albums, artists, playlists, and search across all Music Assistant providers  
🔊 **Optimized Streaming** - Automatic transcoding (FLAC→MP3) for maximum compatibility  
🚀 **Zero Configuration** - Install as Home Assistant addon, auto-discovers Music Assistant  
🎨 **TV-Optimized UI** - Native MSX interface designed for remote control navigation  
🔒 **Secure** - Runs entirely on your local network, no cloud dependencies

## Quick Start

### Prerequisites

- Home Assistant with Supervisor
- [Music Assistant](https://music-assistant.io/) addon installed and running
- [Media Station X](https://msx.benzac.de/) app on your Smart TV

### Installation

1. **Add the addon repository to Home Assistant:**
   ```
   Settings → Add-ons → Add-on Store → ⋮ → Repositories
   Add: https://github.com/your-username/msx-music-assistant
   ```

2. **Install the addon:**
   - Find "MSX Music Assistant Bridge" in the Add-on Store
   - Click Install
   - Configure (see [Configuration Guide](docs/CONFIGURATION.md))
   - Start the addon

3. **Configure MSX on your TV:**
   - Open MSX app
   - Go to Settings → Start Parameter
   - Enter: `http://YOUR_HA_IP:8099/start.json`
   - Restart MSX

4. **Start listening!** 🎶
## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  Smart TV   │ ◄─────► │ Bridge Addon │ ◄─────► │   Music     │
│  (MSX App)  │ HTTP/WS │  (Python)    │ Internal│  Assistant  │
│             │         │              │ Network │             │
│ - UI/Nav    │         │ - Stream     │         │ - Library   │
│ - TypeScript│         │   Proxy      │         │ - Streaming │
│ - Interaction│        │ - Transcode  │         │ - Providers │
└─────────────┘         └──────────────┘         └─────────────┘
```

See [Architecture Documentation](docs/API.md) for details.

## Documentation

- 📖 [Installation Guide](docs/INSTALLATION.md)
- ⚙️ [Configuration Options](docs/CONFIGURATION.md)
- 🔧 [Troubleshooting](docs/TROUBLESHOOTING.md)
- 👨‍💻 [Development Setup](docs/DEVELOPMENT.md)
- 📡 [API Reference](docs/API.md)

## Screenshots

<p align="center">
  <img src="docs/images/screenshots/main-menu.png" width="45%" />
  <img src="docs/images/screenshots/album-view.png" width="45%" />
</p>

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- 🐛 [Report a Bug](https://github.com/your-username/msx-music-assistant/issues/new?template=bug_report.md)
- 💡 [Request a Feature](https://github.com/your-username/msx-music-assistant/issues/new?template=feature_request.md)
- 💬 [Community Forum](https://community.home-assistant.io/t/msx-music-assistant-integration)

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## Credits

- [Music Assistant](https://music-assistant.io/) by Marcel Veldt
- [Media Station X](https://msx.benzac.de/) by Benjamin Zachey
- Inspired by the SoundCloud MSX integration

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
