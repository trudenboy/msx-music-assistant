# Contributing to MSX Music Assistant Integration

Thank you for your interest in contributing! This document provides guidelines and instructions.

## Code of Conduct

Be respectful, inclusive, and professional. We follow the standard open source code of conduct.

## How to Contribute

### Reporting Bugs

Use GitHub Issues with the bug report template. Include:
- Detailed description
- Steps to reproduce
- Expected vs actual behavior
- Environment details (HA version, TV model, etc.)
- Logs from addon and browser console

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

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed setup instructions.

Quick start:
```bash
git clone https://github.com/your-username/msx-music-assistant
cd msx-music-assistant
./scripts/setup-dev.sh
./scripts/test-local.sh
```

## Coding Standards

### Python (Addon)
- Follow PEP 8
- Use Black for formatting
- Type hints for all functions
- Docstrings for public APIs
- Run `pylint` and `mypy` before commit

### TypeScript (Frontend)
- Follow ESLint configuration
- Use Prettier for formatting
- Explicit types, avoid `any`
- JSDoc comments for public APIs

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
- `feat(addon): add MP3 transcoding support`
- `fix(frontend): resolve WebSocket reconnection issue`
- `docs: update installation guide for Tizen`

## Testing

### Addon Tests
```bash
cd addon
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Testing
Use `./scripts/test-local.sh` to run full stack locally.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
