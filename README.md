# Steam Workshop Downloader

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-3.0.0-blue.svg)](https://github.com/c-creatorofficial/steam-workshop-downloader/releases/download/new-versian/steam.workshop.downloader.V3.py)

A zero-setup, single-file CLI application designed for inspecting, crawling, batch-downloading, and extracting Steam Workshop items across all Workshop-enabled games (Garry's Mod, Source Filmmaker, Team Fortress 2, Counter-Strike 2, Half-Life: Alyx, RimWorld, Rust, Terraria, Wallpaper Engine, and more) with advanced security scanning, audit reporting, rate-limiting protection, and automated maintenance features.

No manual environment setup or library installation is required. The script automatically verifies and installs missing Python dependencies on startup.

---

## Overview

Steam Workshop Downloader simplifies fetching and managing Steam Workshop assets. It interfaces directly with Steam Web API endpoints and SteamCMD to fetch content, detects off-site hosting links, automatically decompresses compressed archives (LZMA GMA, VPK, ZIP), scrapes high-resolution preview galleries, and manages multi-threaded batch download queues with robust security and monitoring tools.

---

## Detailed Feature Breakdown

### 1. Universal AppID Support
Supports any Workshop-enabled game on Steam. Includes built-in AppID resolution for popular titles:
- **Garry's Mod (AppID: 4000)**
- **Source Filmmaker (AppID: 1840)**
- **Team Fortress 2 (AppID: 440)**
- **Counter-Strike 2 (AppID: 730)**
- **Half-Life: Alyx (AppID: 546080)**
- **Left 4 Dead 2 (AppID: 550)**
- **RimWorld (AppID: 294100)**
- **Rust (AppID: 252490)**
- **Terraria (AppID: 105600)**
- **Wallpaper Engine (AppID: 431960)**

### 2. Automatic Dependency Bootstrap
On execution, the script checks for required Python modules (`rich`, `requests`, `beautifulsoup4`, `Pillow`). If any package is missing, it automatically installs it using `pip` without breaking runtime flow.

### 3. Archive Processing & Extraction Pipeline
- **Garry's Mod `.gma` Handling:**
  - Performs safe, in-place LZMA decompression for compressed `.gma` files downloaded from Steam CDN.
  - Validates the 4-byte `GMAD` magic header before and after decompression to prevent file corruption.
  - Optional unpacking into loose folder structures using `gmad.exe`.
- **Source Engine `.vpk` Unpacker:**
  - Includes a built-in, pure-Python VPK parser supporting both VPK v1 and v2 formats.
  - Extracts single-file `.vpk` archives as well as multi-part directory layouts (`_dir.vpk` with numbered data chunks like `_000.vpk`).
- **`.zip` Archive Unpacker:**
  - Extracts standard `.zip` payloads with path traversal protections (`..` and absolute path sanitization).

### 4. Lua Guard / Static Security Scanner *(New in v3.0.0)*
Includes a static security analysis engine that automatically scans downloaded `.lua` and `.txt` files for dangerous or suspicious patterns (e.g., `os.execute`, `io.popen`, `http.Fetch`, `file.Write`, and system shell commands) to protect your machine from malicious scripts before execution.

### 5. Archive Integrity Checker & Auto Re-download *(New in v3.0.0)*
Validates ZIP, GMA, and VPK structural integrity prior to extraction. If archive corruption is detected during the verification step, the application automatically triggers a clean re-download.

### 6. Off-Site Cloud Link Detection
Scans workshop item descriptions using regular expressions to identify external hosting links (Google Drive, Mega, Mediafire, Dropbox, Anonfiles, Pixeldrain, SharePoint, OneDrive, Modsfire). If an author uploads a small placeholder file to Steam and hosts the main content externally, the tool displays a prominent warning with the exact URLs.

### 7. Creator Profile Crawler & Collections Parser *(Updated in v3.0.0)*
- **Creator Profiles:** Crawls full Workshop creator profiles across multiple pages (up to 50 pages / 1,500 items). Displays catalog summaries, total combined file size, and provides range-based prompt selection (e.g., `all`, `1-5`, `1, 4, 7`).
- **Steam Collections Parser:** Parses full Steam Workshop collection IDs (`collectionid`) without limits and loads all contained workshop items directly into the download queue.

### 8. Interactive Queue Manager & Batch Import *(Updated in v3.0.0)*
Allows users to queue multiple item URLs, item IDs, collection IDs, or creator profile links.
- **Batch List Import:** Import lists of workshop URLs or IDs directly from external `.txt` files.
- **Queue Backup & Restore:** Save and reload pending or processing download queues via JSON backup files.
- **Sequential Mode:** Downloads items one by one.
- **Concurrent Mode:** Uses multi-threaded worker pools (up to 8 threads) for direct HTTP streaming.

### 9. Scheduled Watchlist & Update Monitor *(New in v3.0.0)*
Tracks added or subscribed workshop items in the background (`watchlist.json`). Automatically queries Steam Web API to check if creators have pushed new updates and alerts the user to update local files.

### 10. Smart Caching & Disk Space Guardian *(New in v3.0.0)*
- **Smart Caching:** Local cache tracking (`download_cache.json`) skips re-downloading files that are already up-to-date locally.
- **Disk Space Guardian:** Inspects local storage before initiating transfers to ensure sufficient free space, including a mandatory 10% safety buffer.

### 11. Resilient Direct HTTP & SteamCMD Engine *(Updated in v3.0.0)*
- **Direct HTTP Streaming:** Downloads via Steam CDN with HTTP `Range` header support for auto-resuming interrupted transfers across up to 4 retry attempts.
- **Bandwidth Throttling:** Configurable download speed limiter (KB/s) for network management.
- **Rate Limiting & Exponential Backoff:** Intelligent handling of HTTP 429 (*Too Many Requests*) status codes with randomized backoff delays.
- **Network Proxy & Custom Headers:** Integrated proxy support (`proxy_url`) and custom HTTP headers for restricted network environments.
- **SteamCMD Fallback:** Automatically switches to SteamCMD if Steam CDN direct links are unavailable. Features live stdout parsing that tracks percentage, stage, transfer speed, and estimated time remaining.

### 12. Preview Gallery Scraper
Scrapes full-resolution screenshot URLs from Workshop item pages, downloads gallery previews, and converts them to standard `.jpg` format at 95% JPEG quality using Pillow.

### 13. Smart Categorization & Audit Reporting *(New in v3.0.0)*
- **Directory Organization:** Automatically categorizes and routes downloaded mods into game-specific and tag-specific folder structures.
- **Audit Logs:** Generates comprehensive CSV and JSON exportable logs detailing download history, bandwidth consumption, external links, and archive integrity results.

---

## Detailed User Guide

### 1. Single Item Inspection & Download
1. Launch the script: `python "steam workshop downloader.py"`.
2. Paste a Workshop item URL or Published File ID (e.g., `https://steamcommunity.com/sharedfiles/filedetails/?id=123456789`).
3. Review the metadata panel (Title, Game, File Size, Engine).
4. If external links are detected, read the warning prompt.
5. Choose whether to run **Lua Guard** security checks, unpack archives (`.gma`, `.zip`, `.vpk`), download preview screenshots, select output directory, and choose output format (loose files or single unified `.zip`).

### 2. Creator Profile & Collection Batch Crawling
1. Paste a creator's Workshop profile URL or a Collection URL (e.g., `https://steamcommunity.com/sharedfiles/filedetails/?id=987654321`).
2. The crawler scans all items/pages and lists available items in a table.
3. Enter selection criteria:
   - `all`: Download all listed items.
   - `1-10`: Download items from index 1 through 10.
   - `1, 3, 7`: Download specific indices.
4. Configure batch download preferences and monitor the batch queue progress.

### 3. Queue Manager & Batch Import
1. Type `queue` at the main prompt.
2. Available queue commands:
   - `add`: Add comma-separated URLs or IDs.
   - `import`: Load items from a `.txt` file containing URLs or Published File IDs.
   - `list`: Render current queue contents.
   - `remove`: Remove specific items by queue number.
   - `backup`: Save the current queue to a JSON backup file.
   - `restore`: Reload a previously saved queue backup.
   - `clear`: Clear the queue.
   - `run`: Process the queue in **Sequential** or **Concurrent** mode.

---

## Current Technical Limitations

1. **SteamCMD Requirement for Restricted Items:**
   Certain games or private/protected Workshop items do not expose direct HTTP CDN links via Steam's Web API. These items require a local installation of `SteamCMD` to download via Steam's network protocol.
2. **Concurrent Downloads Fallback with SteamCMD:**
   When running the Queue Manager in **Concurrent** mode, if any item in the queue requires `SteamCMD`, the application automatically falls back to **Sequential** mode to prevent stdout stream conflicts and filesystem race conditions caused by multiple `SteamCMD` subprocesses.
3. **`gmad.exe` Dependency for Folder Extraction:**
   While `.gma` LZMA decompression is handled natively in Python, extracting `.gma` archives into loose folder structures requires `gmad.exe` (included with Garry's Mod installation).
4. **Off-Site Cloud Downloads:**
   The external cloud link detector identifies off-site mirrors (Google Drive, Mega, Mediafire, etc.) and presents them to the user, but cannot automatically bypass host captchas or download files from third-party cloud providers.
5. **Steam Web Scraping & Profile Privacy:**
   - Creator profile crawling relies on public web pages. Profiles set to Private or Friends-Only cannot be crawled.
   - Profile crawling is capped at 50 pages (30 items per page, up to 1,500 items max).
   - High-frequency requests are mitigated by automatic exponential backoff, but extreme loads may still trigger temporary Steam HTTP 429 rate-limiting.

---

## Requirements

- **Python 3.8+**
- *(Optional)* **SteamCMD** — Required for items that do not provide direct CDN download links.
- *(Optional)* **gmad.exe** — Required for extracting Garry's Mod `.gma` files into loose folders.
