# Changelog

All notable changes to the **Steam Workshop Downloader** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-10-09

### Added
- **Universal AppID Support:** Added full compatibility for downloading content across ALL Steam Workshop games (TF2, CS2, HL: Alyx, L4D2, RimWorld, Rust, Terraria, etc.).
- **Built-in VPK Unpacker:** Integrated a pure-Python `.vpk` archive extractor capable of handling single and multi-part archives natively without third-party tools.
- **Queue Manager & Concurrency:** Added interactive download queue management supporting both **Sequential** and **Concurrent** (multi-threaded) execution modes.
- **External Cloud Link Detector:** Added automatic regex scanning in item descriptions for off-site mirrors (Google Drive, Mega, Mediafire, Dropbox, etc.) with prominent warning UI.
- **Real-Time SteamCMD Progress Stream:** Added live progress, speed, and time-remaining tracking for SteamCMD downloads directly in the terminal interface.
- **Error Logging System:** Automated stack-trace logging saved to `error_log.txt` for easier crash debugging.

### Changed
- **LZMA Decompression Engine:** Improved `.gma` LZMA decompression with file-lock safety, pipeline verification, and automatic fallback handling.
- **Creator Profile Crawler:** Upgraded crawler to handle multi-page creator profile parsing with dynamic batch selection (e.g., `1-5`, `all`).
- **Interactive TUI:** Enhanced terminal user interface with styled tables, progress indicators, and status updates using Rich.

### Fixed
- Fixed WinError 32 file locking issues during in-place LZMA decompression on Windows.
- Resolved URL query parameter stripping issues when parsing steam profile links.

---

## [1.0.0] - Initial Public Release

### Added
- Single-file CLI script with automatic dependency installation (auto-bootstrap).
- Direct HTTP streaming downloader with HTTP Range header resume support.
- Initial Garry's Mod (`.gma`) decompression and `gmad.exe` extraction pipeline.
- Preview image scraper and conversion to `.jpg`.
- Persistent config management via `~/.steam_workshop_downloader/config.json`.