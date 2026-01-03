# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-01-03

### Added
- **Session Encryption**: Optional AES-256 encryption (Fernet) for session files with secure key storage via `keyring`.
- **Async I/O**: Completed migration of the session management layer to a fully non-blocking architecture using `aiofiles`.
- **Comprehensive Provider Tests**: Added robust timeout and API error handling tests for Anthropic and OpenRouter providers.
- **Security Documentation**: Created `SECURITY.md` covering privacy, injection defense, and best practices.

### Fixed
- **OOM Prevention**: Added input size limits (10MB) for stdin and file reads to prevent memory exhaustion attacks.
- **Atomic Config Saves**: Implemented a temporary-file-and-rename pattern for configuration saves to prevent file corruption.
- **Specific Exception Handling**: Replaced broad exception catching in OpenAI and OpenRouter providers with specific SDK exception types for better error visibility.

### Changed
- Converted `SessionManager` methods to `async` and updated all CLI call sites to improve responsiveness.

## [0.3.0] - 2026-01-02

### Added
- Manual workflow trigger support for publish.yml (workflow_dispatch)
- PyPI package name documentation in __init__.py

### Fixed
- PyPI publishing automation with manual trigger capability
- Build workflow now correctly uses release tag via workflow_dispatch input

### Changed
- Improved publish.yml to support both automated and manual publishing workflows

## [0.2.0] - 2026-01-02

### Added
- First PyPI release as `nexus-ai-cli`
- GitHub Actions workflows for automated versioning and publishing

### Fixed
- Ensure publishing workflow builds from the release tag

## [0.1.0] - 2026-01-01

### Added
- Initial release
- Multi-provider AI CLI framework
- OpenAI, Anthropic, Ollama, OpenRouter support
- Session management
- Prompt library
- Streaming output
