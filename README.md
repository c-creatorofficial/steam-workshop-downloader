# Steam Workshop Downloader

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A zero-setup, single-file CLI tool for inspecting, crawling, and batch-downloading Steam Workshop items for **Garry's Mod** (AppID 4000) and **Source Filmmaker** (AppID 1840).

No manual dependency installation needed — just run the script and it handles everything automatically.

---

## Features

* **Zero Setup (Auto-Bootstrap):** Automatically checks and installs required packages (`rich`, `requests`, `bs4`, `Pillow`) on first run.
* **Single-File Utility:** The entire application lives inside a single script for maximum portability.
* **Smart Link Detection:** Automatically scans item descriptions for off-site hosting links (Google Drive, Mega, Mediafire, etc.).
* **Automatic `.gma` Decompression:** Safe in-place LZMA decompression for Garry's Mod files.
* **Optional Unpacking (`gmad.exe`):** Direct extraction pipeline for Garry's Mod `.gma` archives.
* **Creator Profile Crawler:** Crawls full creator profiles to inspect and batch-download entire collections.
* **Resilient Downloads:** Direct HTTP streaming with auto-resume logic, falling back to SteamCMD when needed.
* **Gallery Scraper:** Scrapes full-res preview gallery images and converts them to `.jpg`.

---

## Requirements

* **Python 3.8+**
* *(Optional)* **SteamCMD** — for items requiring Steam network authentication.
* *(Optional)* **gmad.exe** — for unpacking Garry's Mod `.gma` files into folders.

---

## Quick Start

1. **Clone or Download the Repository:**
   ```bash
   git clone https://github.com/your-username/steam-workshop-downloader.git
   cd steam-workshop-downloader
   ```

2. **Run the Application:**
   ```bash
   python main.py
   ```

---

## Configuration & Logs

* **Config:** Paths and settings are saved automatically at `~/.steam_workshop_downloader/config.json`.
* **Logs:** Any unexpected crash details are recorded locally in `error_log.txt`.

---

## License

Distributed under the [MIT License](LICENSE).
