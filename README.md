# Steam Workshop Downloader

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat)](LICENSE)
[![Version](https://img.shields.io/badge/Version-4.0.0-blue.svg)](https://github.com/c-creatorofficial/steam-workshop-downloader/releases/)

A single-file, interactive CLI application for inspecting, crawling, downloading, extracting, and organizing Steam Workshop content across Workshop-enabled games. It combines direct Steam CDN downloads with SteamCMD fallback, creator and collection crawling, batch queues, archive processing, update monitoring, security checks, audit reports, and configurable local storage.

The application verifies its core Python dependencies on startup and installs missing or outdated packages automatically. Optional integrations are installed only when the selected storage or security feature requires them.

---

## Overview

Steam Workshop Downloader provides a complete workflow for collecting and managing Workshop content. Enter a Workshop item ID, item URL, creator profile, or collection URL to retrieve available metadata and send the selected content through the download pipeline.

The downloader uses Steam Web API endpoints and public Steam Community pages to resolve item information. When a direct Steam CDN URL is available, files are streamed over HTTP with resume support. Items without a usable direct link can be retrieved through SteamCMD when it is installed and configured.

Downloaded content can be kept in its original format, extracted into folders, or packaged into individual ZIP archives. The application also checks archive integrity, scans supported GMA payloads with Lua Guard, records download activity, tracks Workshop updates, and keeps local cache and queue state between sessions.

---

## Detailed Feature Breakdown

### 1. Universal AppID Support

Supports Workshop-enabled Steam games through their AppIDs. The application includes built-in display-name mappings for commonly used titles and falls back to a generic Steam Workshop game label when an AppID is not in the list.

- **Garry's Mod (AppID: 4000)**
- **Source Filmmaker (AppID: 1840)**
- **Team Fortress 2 (AppID: 440)**
- **Counter-Strike: Global Offensive / Counter-Strike 2 (AppID: 730)**
- **Half-Life: Alyx (AppID: 546080)**
- **Left 4 Dead 2 (AppID: 550)**
- **Dota 2 (AppID: 570)**
- **Portal 2 (AppID: 620)**
- **Half-Life 2 (AppID: 220)**
- **Fallout 4 (AppID: 377160)**
- **The Elder Scrolls V: Skyrim Special Edition (AppID: 489830)**
- **RimWorld (AppID: 294100)**
- **Don't Starve Together (AppID: 322330)**
- **Unturned (AppID: 304930)**
- **ARK: Survival Evolved (AppID: 346110)**
- **Space Engineers (AppID: 244850)**
- **Cities: Skylines (AppID: 255710)**
- **Stellaris (AppID: 281990)**
- **Europa Universalis IV (AppID: 236850)**
- **Hearts of Iron IV (AppID: 394360)**
- **Sid Meier's Civilization VI (AppID: 289070)**
- **Terraria (AppID: 105600)**
- **Starbound (AppID: 211820)**
- **The Forest (AppID: 242760)**
- **No Man's Sky (AppID: 275850)**
- **Wallpaper Engine (AppID: 431960)**
- **Rust (AppID: 252490)**
- **Euro Truck Simulator 2 (AppID: 227300)**
- **Rocket League (AppID: 252950)**

The built-in list is used for identification and display. Actual metadata and download availability still depend on the selected game's Workshop configuration and Steam's response.

### 2. Automatic Dependency Bootstrap

The startup resolver checks both package availability and minimum installed versions before launching the application.

**Core dependencies:**
- `rich >= 13.0.0`
- `requests >= 2.28.0`
- `beautifulsoup4 >= 4.11.0`
- `Pillow >= 9.0.0`

Missing or outdated core packages are installed or upgraded through the active Python interpreter. Optional packages are checked only when the relevant feature is enabled or used:
- `sqlcipher3 >= 0.6.4` — encrypted SQLite storage.
- `cryptography >= 42.0.0` — optional AES-GCM protection for JSON data and encrypted backups.
- `keyring >= 25.6.0` — OS-backed key storage for selected SQLite key and authenticated-proxy configurations.

The bootstrap verifies the installed package after installation. Startup stops safely when a dependency required by the active configuration cannot be installed or verified.

### 3. Workshop Metadata, Creator Crawler & Collections Parser

- **Single Item Lookup:** Retrieves available Workshop metadata such as title, creator, game, file size, description, tags, update information, and direct download details.
- **Creator Profiles:** Crawls public Workshop creator pages, follows available pagination links, collects unique item IDs, and reports partial results when Steam returns an error or repeated page content.
- **Steam Collections:** Parses collection pages and adds the contained Workshop items to the download queue.
- **Dependency Resolution:** Detects required Workshop items from an item's page and offers to include those prerequisites in the download process.
- **Catalog Persistence:** Saves crawled catalog information locally so it can be revisited and used to create custom queues.

Catalog information is based on metadata returned by Steam. Missing values are kept as unknown instead of being replaced with guessed data.

### 4. Catalog Filtering, Sorting & Custom Queues

Creator catalogs can be reviewed and narrowed down before downloading. Available filters include:
- Text search across title, item ID, creator, tags, and description.
- Included and excluded tags.
- Category-oriented filtering for models, maps, gameplay-related content, and other items.
- Download status, including downloaded, incomplete, and failed items.
- Minimum and maximum file size.
- Update date range.
- Popularity range when Steam provides usable favorites or subscription metadata.

Catalogs can be sorted by original order, popularity, update date, file size, title, or item ID. Catalog numbering remains stable when filters or sorting are changed, making range-based selection predictable.

Selected catalog entries can be downloaded immediately or saved as named custom queues. Custom queues retain their items and download status and can be reviewed, rebuilt, or removed independently of the regular queue.

### 5. Interactive Queue Manager & Batch Import

The queue manager accepts Workshop item URLs and Published File IDs. It supports:
- Add, list, remove, and clear operations.
- Sequential or concurrent queue processing.
- JSON queue backup and restore.
- Importing item lists from external `.txt` files.
- Saved custom queues created from creator catalogs.
- Queue progress summaries showing completed, failed, skipped, and unattempted items.

The dedicated TXT importer validates and deduplicates entries, displays the imported catalog, and allows selected items to be added or removed before queueing. The source text file is not modified. Import selection state is saved locally so the catalog can be revisited.

Concurrent queue mode supports up to 8 download workers for direct HTTP items. If a queue contains an item that requires SteamCMD, the application switches that queue run to sequential mode to avoid conflicting SteamCMD subprocess output and filesystem operations.

### 6. Archive Processing & Extraction Pipeline

- **Garry's Mod `.gma` Handling:**
  - Performs native LZMA decompression for compressed GMA payloads.
  - Checks the `GMAD` header and validates the archive structure.
  - Uses `gmad` for optional extraction into a loose folder structure.
  - Validates the GMA manifest, member paths, output file sizes, and supplied CRC32 values after extraction.
- **Source Engine `.vpk` Unpacker:**
  - Includes a built-in Python VPK parser for VPK v1 and v2.
  - Supports single-file VPK archives and multi-part layouts such as `_dir.vpk` with numbered data chunks.
- **`.zip` Archive Unpacker:**
  - Extracts ZIP payloads while checking archive paths and member data.
  - Rejects unsafe paths, absolute paths, traversal entries, unsupported special-file entries, and conflicting output paths.
  - Applies archive member-count, expanded-size, and compression-ratio limits.

Extraction can be enabled independently for GMA, ZIP, and VPK content. The original downloaded payload can remain available alongside the extracted output.

### 7. Archive Integrity Checker & Automatic Re-download

ZIP, GMA, and VPK payloads are checked before extraction when their structure can be validated.
- ZIP checks include member readability, CRC validation, path safety, and expanded-size limits.
- GMA checks include the GMAD structure, file manifest, member metadata, and available CRC information.
- VPK checks validate the directory structure and referenced data sections.
- Invalid direct HTTP payloads trigger a clean re-download attempt. SteamCMD downloads receive an additional integrity retry when validation fails.

The V4 download pipeline writes HTTP transfers to a temporary sidecar file and publishes the completed payload only after the expected size and supported-format checks pass. Existing output is not replaced by an incomplete transfer.

### 8. Lua Guard / Static Security Scanner

Lua Guard performs static inspection of Lua content found inside supported GMA payloads. It looks for suspicious or potentially dangerous operations, including process execution, shell commands, file writes, and potentially risky network-related calls.

The scanner does not execute the inspected code. Its findings are heuristic warnings and may include false positives. A clean scan does not guarantee that an addon is safe. In the supplied V4 build, the Lua Guard setting is explicitly scoped to GMA files.

### 9. Off-Site Cloud Link Detection

Scans Workshop item descriptions for known external hosting links, including:
- Google Drive
- Mega
- MediaFire
- Dropbox
- Anonfiles
- Pixeldrain
- SharePoint
- OneDrive short links
- Modsfire

When an item uses Steam as a placeholder and references an external mirror, the application displays the detected URLs before the download workflow continues.

### 10. Resilient Direct HTTP & SteamCMD Engine

- **Direct HTTP Streaming:** Downloads available Steam CDN files using streamed HTTP requests.
- **Range Resume:** Resumes interrupted transfers with HTTP `Range` requests and validates `206 Partial Content`, `416 Range Not Satisfiable`, `Content-Range`, and expected payload length before accepting the result.
- **Retry Handling:** Retries interrupted or failed transfers and resumes from the verified local offset where possible.
- **Atomic Publication:** Uses a temporary download file and moves it into the final destination only after validation succeeds.
- **SteamCMD Fallback:** Uses SteamCMD when the Web API does not expose a usable direct CDN URL or the direct transfer cannot produce a valid payload.
- **Live SteamCMD Progress:** Parses process output to display download stage, progress, transfer information, and estimated time where available.
- **Process Timeouts:** Monitors external process execution and terminates the process tree when a SteamCMD or GMA extraction operation exceeds its allowed runtime.

SteamCMD and direct HTTP are used as complementary download paths. The application does not bypass Workshop permissions or restrictions.

### 11. Network Controls, Rate Limiting & Proxy Support

- **HTTP Request Pacing:** Configurable simultaneous request count, minimum per-host request interval, retry count, and maximum automatic `Retry-After` wait.
- **Rate-Limit Handling:** Handles HTTP 429 responses with bounded retry and backoff behavior rather than repeatedly sending requests without delay.
- **Download Speed Limiter:** Applies a configurable KB/s bandwidth limit across HTTP download workers.
- **Proxy Configuration:** Supports explicit HTTP/HTTPS proxies, host-and-port values, operating-system/environment proxy detection, and direct connections.
- **Authenticated Proxies:** Proxy usernames and passwords are stored through a recognized OS keyring backend rather than being kept in the normal configuration file.
- **Diagnostic Redaction:** Removes credential-shaped values and sensitive URL data from application error logs where recognized.

Network pacing settings are intended to reduce request pressure and respect server limits; they do not circumvent Steam rate limits.

### 12. Smart Caching & Disk Space Guardian

- **Version-aware Cache:** Stores Workshop item update timestamps and local download paths. Items already downloaded at the current Workshop update time can be skipped during later batch runs.
- **Payload Validation:** A cache entry is not treated as complete when its local file or directory is missing, empty, or contains only preview images.
- **Disk Space Check:** Estimates the total size of queued items and checks free space before starting a batch. The check includes a 10% buffer and an additional 100 MB margin.
- **Queue Status Tracking:** Keeps completed, failed, pending, and downloading item states for queue summaries and catalog filters.

### 13. Scheduled Watchlist & Update Monitor

Tracks selected Workshop item IDs in a persistent watchlist. The scheduler periodically checks Steam metadata for changes to the tracked items and notifies the user when an update is available.

Watchlist controls include:
- Add or remove items by URL or ID.
- List tracked items.
- Set the update-check interval.
- Enable or disable scheduled checks.
- Run an immediate manual check.

The default configured interval is 24 hours. The interval can be changed from the Watchlist menu or Settings.

### 14. Preview Gallery Scraper

Scrapes Workshop item pages for the main preview and available gallery screenshots. It downloads the original image files and converts supported images to standard `.jpg` files using Pillow at 95% JPEG quality.

Preview files are stored in a dedicated `previews` directory within the item's download workspace.

### 15. Smart Categorization & Folder Organization

Downloaded items can be organized into game-specific and tag-based folder structures. The categorization step uses the Workshop metadata available for the item and keeps each downloaded item's own workspace separate.

### 16. Audit Reporting

When audit reporting is enabled, the application records download activity and relevant item information, including:
- Item ID, title, AppID, and game name.
- Download source (direct HTTP or SteamCMD).
- Expected file size and transferred bytes.
- Destination path and final download status.
- Archive integrity result.
- Detected external links.
- Lua Guard scan status and warning count.
- Error details when an operation fails.

Audit history can be exported to **CSV** or **JSON** for review and record keeping.

### 17. Storage Management, Encryption & Backups

V4 supports two local storage backends:
- **JSON:** The legacy file-based storage mode.
- **SQLite:** A structured database backend for cache entries, audit history, download status, crawled catalogs, and custom queues.

The storage manager can migrate existing JSON data into SQLite, export SQLite data back to JSON, inspect storage status, and create backups. Migration routines verify imported records and retain the original JSON source files.

**Encryption options:**
- SQLite storage uses SQLCipher when the SQLite backend is active. Its key can be protected through Windows DPAPI, a recognized OS keyring, or a passphrase-based fallback.
- JSON-mode data files can optionally be protected with AES-GCM encryption.
- Backup archives can optionally be encrypted and saved with the `.swdenc` extension.
- Encrypted backups can be decrypted into a ZIP archive for manual inspection or restoration workflows.

The application also supports changing the internal data directory and SQLite database path. The internal data directory is separate from the Workshop download destination.

### 18. Interactive Terminal UI & Error Logging

Uses Rich to render terminal panels, tables, prompts, progress bars, transfer speeds, and time estimates. Configuration is stored between runs, while critical exceptions and tracebacks are written to `error_log.txt` with sensitive diagnostic values redacted where recognized.

---

## Detailed User Guide

### 1. Installation & First Launch

1. Make sure Python 3.10 or newer is installed.
2. Place the script in a directory where it can be run and where it has permission to write its configuration and download data.
3. Launch the application:

   ```bash
   python "steam workshop downloader V4.py"
   ```

4. On startup, the script checks the required packages and installs or upgrades missing dependencies.
5. The default internal configuration directory is `~/.steam_workshop_downloader`. The default Workshop download directory is `~/Downloads/SteamWorkshop`.

### 2. Single Item Inspection & Download

1. Enter a Workshop item URL or Published File ID at the main prompt.
2. Review the metadata panel, including the title, game, creator, file size, and available Workshop information.
3. Review any external hosting links detected in the item description.
4. Choose whether to include detected prerequisites, run the available Lua Guard checks, unpack GMA/ZIP/VPK archives, and download preview images.
5. Select the output directory and choose whether to keep the downloaded payload or create an individual ZIP archive.
6. Confirm the operation and monitor the progress display.

Example item URL:

```text
https://steamcommunity.com/sharedfiles/filedetails/?id=123456789
```

### 3. Creator Profile Crawling & Catalog Selection

1. Paste a creator's Steam Workshop profile or Workshop listing URL.
2. The crawler follows the available Steam pagination controls and collects unique Workshop item IDs.
3. Review the catalog and use the filter and sort actions to narrow down the list.
4. Select entries using one of the supported formats:
   - `all` — select every item currently shown.
   - `1-10` — select a range of catalog numbers.
   - `1, 3, 7` — select individual catalog entries.
5. Download the selected items or use `new queue` to save them as a named custom queue.

Catalog filters and sorting do not modify the creator's Workshop page. Items with missing metadata remain identifiable as unknown rather than receiving estimated values.

### 4. Steam Collection Download

1. Paste a Steam Workshop collection URL.
2. The collection parser retrieves the contained item IDs and removes duplicates.
3. Confirm whether the collection should be sent to the download queue immediately.
4. Review the queue settings and start the download process.

Example collection URL:

```text
https://steamcommunity.com/workshop/collection/?id=987654321
```

### 5. Queue Manager & Batch Import

Type `queue` at the main prompt to open the queue manager.

Available queue actions:
- `add` — add comma-separated Workshop URLs or IDs.
- `list` — display the current queue.
- `remove` — remove selected queue entries by number or range.
- `clear` — clear the queue after confirmation.
- `run` — process the queue in sequential or concurrent mode.
- `import_txt` — import a text file containing Workshop URLs or IDs.
- `backup` — save the current queue to a JSON backup.
- `restore` — load entries from the saved queue backup.
- `custom` — manage saved custom queues.

The main prompt also accepts `import_txt` to open the dedicated TXT catalog importer directly. Imported entries can be reviewed, selected, removed, exported, and queued without editing the original `.txt` file.

### 6. Watchlist & Reports

- Type `watch` to manage tracked Workshop items and run update checks.
- Type `report` to export the audit history to CSV or JSON.
- Type `docs` to display the built-in English usage guidelines.

### 7. Settings & Storage

Type `settings` to configure the application. The Settings menu includes:
- Data directory and download directory.
- JSON or SQLite storage backend and SQLite database path.
- JSON encryption, encrypted backups, and backup decryption.
- HTTP request concurrency, request interval, retry attempts, and `Retry-After` wait ceiling.
- Proxy configuration and authenticated proxy credentials.
- SteamCMD and `gmad` executable paths.
- Download speed limit.
- Lua Guard, audit reporting, and watchlist scheduling.
- Storage health checks and application setting reset.

Review the confirmation prompts before changing data directories, migrating storage, resetting settings, or modifying encryption options. Keep the relevant encryption key or passphrase and a separate backup before switching storage configurations.

---

## Current Technical Limitations

1. **SteamCMD Requirement for Restricted Items:**
   Some games and Workshop items do not expose direct HTTP CDN links through Steam's Web API. These items require a working local SteamCMD installation. Availability may also be affected by item visibility, ownership, game requirements, and Steam-side restrictions.

2. **Concurrent Downloads with SteamCMD:**
   Concurrent queue mode is intended for direct HTTP downloads. If one or more queued items require SteamCMD, the application automatically switches the queue to sequential mode to avoid conflicts between SteamCMD subprocesses.

3. **`gmad` Requirement for GMA Folder Extraction:**
   GMA LZMA decompression and structural checks are handled in Python. Extracting a GMA archive into a loose folder requires a valid `gmad` executable, normally available with a Garry's Mod installation.

4. **Off-Site Cloud Downloads:**
   The external link detector identifies supported third-party hosting URLs and displays them to the user. It does not automatically download files from those services or bypass captchas, access restrictions, or provider-specific confirmation pages.

5. **Steam Profile Visibility & Web Scraping:**
   Creator crawling depends on public Steam Community pages. Private, Friends-Only, unavailable, or restricted profiles may not be crawlable. Pagination and item extraction depend on Steam's current page structure; repeated or incomplete pages are detected where possible, but a Steam website change can still affect crawling. High request volumes may receive HTTP 429 responses or temporary restrictions.

6. **Workshop Metadata Availability:**
   File size, tags, update dates, popularity information, and other catalog fields are supplied by Steam. Some items may not expose every field. Filters preserve items with unknown metadata unless another active filter excludes them.

7. **Lua Guard Scope:**
   Lua Guard is a static heuristic scanner, not a sandbox or antivirus engine. In this V4 build it is scoped to GMA payloads. It does not execute scripts and cannot guarantee that scanned content is safe.

8. **Archive Format Support:**
   Built-in extraction is provided for GMA, ZIP, and VPK files. Other archive formats are not guaranteed to be extractable by the application.

9. **Optional Storage & Security Dependencies:**
   SQLite encryption, JSON encryption, and authenticated-proxy credential storage require their respective optional packages and supported system facilities. If the relevant library or secure OS keyring is unavailable, the related feature may not be usable. Losing an encryption passphrase or protected key can make encrypted data inaccessible.

10. **Dependency Installation:**
    Automatic dependency installation requires a working Python `pip` environment, internet access, and permission to install packages. If installation fails, the startup message provides the package command that needs to be run manually.

---

## Requirements

- **Python 3.10+**
- **Core Python packages** — Automatically checked and installed: `rich`, `requests`, `beautifulsoup4`, and `Pillow`.
- *(Optional)* **SteamCMD** — Required for Workshop items that cannot be downloaded through a direct CDN link.
- *(Optional)* **`gmad`** — Required for extracting Garry's Mod `.gma` files into loose folders.
- *(Optional)* **`sqlcipher3`** — Required when using encrypted SQLite storage.
- *(Optional)* **`cryptography`** — Required for optional AES-GCM JSON encryption and encrypted backup archives.
- *(Optional)* **`keyring`** — Required for OS-keyring-backed SQLite key storage or authenticated proxy credentials.

---

## Version History

### Version 1.0.0 — Initial Public Release

The first release established the core Workshop download workflow, focused on Garry's Mod and Source Filmmaker.

- Added Steam Workshop item metadata lookup and creator profile crawling.
- Added initial AppID mappings for Garry's Mod and Source Filmmaker.
- Added automatic dependency installation for the core Python packages.
- Added persistent configuration for the download directory, SteamCMD path, and `gmad` path.
- Added automatic LZMA decompression for compressed GMA files and optional extraction through `gmad`.
- Added direct HTTP downloads with resume support and retry handling.
- Added SteamCMD fallback with live download progress and output validation.
- Added external cloud hosting link detection in Workshop descriptions.
- Added Workshop preview scraping and JPEG conversion.
- Added Rich-based terminal panels, metadata tables, and error logging.

### Version 2.0.0 — Universal Workshop & Archive Support

The second release expanded the downloader beyond its original two-game focus and introduced archive extraction and queue-based downloads.

- Expanded built-in AppID mappings to a broad range of Steam Workshop games.
- Added generic AppID display-name fallback for games not in the built-in list.
- Added automatic ZIP extraction with path sanitization.
- Added a native Python VPK extractor with VPK v1/v2 support and multi-part archive handling.
- Added independent GMA, ZIP, and VPK extraction options.
- Added automatic payload extension detection for supported archive types.
- Added the interactive download queue with add, list, remove, clear, and run operations.
- Added concurrent HTTP queue processing through a worker pool.
- Improved metadata handling and queue presentation for batch downloads.

### Version 3.0.0 — Merged Edition & Download Management

The third release combined the original downloader with the extension features and introduced persistent download management, network controls, and security checks.

- Added Steam Workshop collection parsing and collection-to-queue processing.
- Added Workshop prerequisite/dependency detection and optional dependency downloads.
- Added TXT batch-list import and queue backup/restore.
- Added concurrent queue controls with up to 8 workers for direct HTTP downloads and sequential fallback for SteamCMD items.
- Added HTTP 429 handling, exponential backoff, proxy configuration, and download speed throttling.
- Added version-aware local caching to skip items that are already up to date.
- Added queue and download status persistence.
- Added disk space checks with a safety margin before batch downloads.
- Added game- and tag-based download categorization.
- Added scheduled Watchlist monitoring for Workshop item updates.
- Added ZIP, GMA, and VPK integrity checks with automatic re-download on detected corruption.
- Added Lua Guard static scanning for suspicious script patterns.
- Added CSV and JSON audit reporting.
- Added improved batch processing, queue progress, and network handling.

### Version 4.0.0 — Stable Build, Storage & Security Hardening

The fourth release retained the V3 download and management features and expanded the application with stronger data handling, more detailed catalog management, and safer download/extraction operations.

- Reworked dependency bootstrap to verify installed package versions and install optional integrations only when required.
- Added configurable JSON and SQLite storage backends, SQLCipher database encryption, and verified JSON-to-SQLite / SQLite-to-JSON migration.
- Added optional AES-GCM encryption for JSON data and encrypted `.swdenc` backup archives.
- Added protected SQLite key handling through Windows DPAPI, supported OS keyrings, or a passphrase-based fallback.
- Added authenticated proxy support with credentials stored in the OS keyring and redaction of sensitive diagnostic values.
- Added a configurable data directory, SQLite path management, storage health checks, and consistent backup handling.
- Added creator catalog filtering and sorting by text, tags, category, download status, size, date, popularity, title, and item ID.
- Added persistent custom queues built from filtered creator catalogs.
- Added a dedicated TXT catalog importer with validation, duplicate removal, interactive selection, saved import state, and export support.
- Improved creator crawling with pagination diagnostics, repeated-page detection, and partial-result handling.
- Improved request pacing, bounded retries, `Retry-After` handling, and global download speed throttling.
- Improved direct HTTP resume validation using response ranges, expected lengths, temporary sidecar files, and atomic publication.
- Added stricter archive validation and transactional extraction for ZIP, GMA, and VPK payloads.
- Added GMA manifest validation, output size/CRC checks, extraction staging, and external-process timeouts.
- Improved SteamCMD process monitoring, output decoding, timeout handling, and process-tree termination.
- Improved cache validation, queue progress summaries, thread-safe state updates, and storage-aware Watchlist and audit operations.

The supplied V4 script reports `VERSION = "4.0.0"` and identifies itself as the Stable build. It also contains the later maintenance and hardening layers integrated into that source file.

---

## License

This project is distributed under the MIT License. See the `LICENSE` file for details.
