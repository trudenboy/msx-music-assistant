# Contributing to MSX Music Assistant Bridge

Thank you for your interest in contributing! This document provides guidelines and instructions.

## Code of Conduct

Be respectful, inclusive, and professional. We follow the standard open source code of conduct.

## How to Contribute

### Reporting Bugs

Use GitHub Issues with the bug report template. Include:
- Detailed description
- Steps to reproduce
- Expected vs actual behavior
- Environment details (MA version, TV model, MSX app version)
- Logs from the MA server

### Suggesting Features

Use GitHub Issues with the feature request template. Explain:
- Use case and problem it solves
- Proposed solution
- Alternative approaches considered
- Willingness to implement

### Pull Requests

1. **Fork and clone the repository**
2. **Create a feature branch:** `git checkout -b feature/your-feature-name`
3. **Make your changes** following coding standards
4. **Test thoroughly** (see Testing section)
5. **Commit with clear messages**
6. **Update documentation**
7. **Push to your fork**
8. **Submit pull request** to `main` branch

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (used by MA for venv/dependency management)
- MA server fork cloned alongside this project

### Quick Start

```bash
git clone https://github.com/trudenboy/msx-music-assistant.git
cd msx-music-assistant

# Setup venv, install deps, symlink provider into MA server
./scripts/link-to-ma.sh

# Activate the MA venv (required for all commands)
source /Users/renso/Projects/ma-server/.venv/bin/activate
```

See [CLAUDE.md](CLAUDE.md) for detailed development guidance, architecture, and MA conventions.

## Coding Standards

### Python

- Follow PEP 8
- `from __future__ import annotations` at the top of every file
- Type hints on all functions
- All I/O uses async/await (aiohttp)
- Follow patterns from MA reference providers (`_demo_player_provider`, `sendspin`)
- Run pre-commit before committing:
  ```bash
  source /Users/renso/Projects/ma-server/.venv/bin/activate
  cd /Users/renso/Projects/ma-server && pre-commit run --all-files
  ```

### TypeScript (future)

The `frontend/` directory contains scaffolding for a full MSX TypeScript plugin. This is not yet active — the provider currently serves an inline JS interaction plugin. TypeScript guidelines will be added when this becomes active.

### Commit Messages

Format: `type(scope): description`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
- `feat(provider): add search endpoint for MSX content pages`
- `fix(player): correct elapsed time calculation on pause`
- `docs: update README with architecture diagrams`

## Testing

All tests must run inside the MA venv:

```bash
source /Users/renso/Projects/ma-server/.venv/bin/activate
```

### Unit Tests

```bash
pytest tests/ -v --ignore=tests/integration
```

### Integration Tests

Integration tests require a running MA server and are in `tests/integration/`:

```bash
pytest tests/integration/ -v
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
