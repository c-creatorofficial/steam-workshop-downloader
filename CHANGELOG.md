# Changelog - Steam Workshop Downloader

## [2.0.0] - Version 2.0.0 Major Update

### 🚀 Major New Features

1. **Universal Steam AppID Support**
   - **Expanded Game Database:** Added native recognition for over 28 popular Steam games (including *Team Fortress 2*, *CS:GO / CS2*, *Half-Life: Alyx*, *Left 4 Dead 2*, *RimWorld*, *Skyrim SE*, *Terraria*, *Wallpaper Engine*, *Rust*, etc.).
   - **Dynamic Display Resolution:** Added `get_app_display_name()` to handle any valid Steam Workshop AppID beyond Garry's Mod and SFM.

2. **Interactive Download Queue Manager**
   - **Queue Commands:** Added a full-featured queue sub-system accessible via `queue` command (`add`, `list`, `remove`, `clear`, `run`, `back`).
   - **Batch Processing:** Allows users to queue multiple individual item IDs, workshop links, or creator profiles together.
   - **Concurrent Downloads:** Integrated `ThreadPoolExecutor` supporting multi-threaded parallel downloads (up to 8 workers) with automatic fallback to sequential mode for SteamCMD downloads.

3. **Built-in VPK Archive Extractor**
   - **Pure-Python Unpacker:** Added `VPKExtractor` class to parse and extract VPK (v1 & v2) archive files without requiring external software.
   - **Multi-part Archive Support:** Supports split/chunked VPK files (e.g., `_dir.vpk` and `_000.vpk`).
   - **Auto-Extract VPK:** Integrated `auto_vpk` pipeline option to extract VPK files automatically post-download.

4. **ZIP Archive Extraction Engine**
   - Added `extract_zip_file()` and `auto_unpack_zip_payload()` to automatically detect and unpack downloaded `.zip` archives and nested ZIP files.

---

### 🛠 Improvements & Refinements

- **Smart Payload Extension Detection:** Replaced rigid `.gma` vs `.zip` logic with `guess_payload_extension()`, dynamically detecting `.gma`, `.zip`, `.vpk`, `.rar`, `.7z`, `.tar`, and `.gz` from CDN URLs.
- **Config & Settings Update:** Expanded `AppConfig` dataclass with `auto_unzip` and `auto_vpk` fields while preserving backward compatibility with existing config files.
- **Enhanced Terminal UI (TUI):** Updated banners, tables, and prompts to reflect multi-game support, extraction choices, and download queue actions.

---

### 🐛 Bug Fixes & Stability Improvements

- Improved file handle management in `decompress_gma_lzma()` to eliminate file lock issues (`WinError 32`) on Windows.
- Safer path traversal prevention (`_safe_target`) during archive extraction.
