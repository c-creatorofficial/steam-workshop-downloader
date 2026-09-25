#!/usr/bin/env python3
"""
Steam Workshop Downloader
=========================================================
Version: 1.0.0 (Public)
Author: c.c

Advanced CLI utility to inspect, crawl, batch-download, and archive
Garry's Mod (AppID: 4000) and Source Filmmaker (AppID: 1840) addons.

Includes:
- External Cloud Link Detector (Google Drive, Mega, Mediafire, etc.)
- Interactive SteamCMD & gmad.exe Path Resolver with Persistent Config
- Automatic LZMA Decompression for Steam CDN .gma files (File-Lock Safe)
- Optional Auto-Extract Mechanism using gmad.exe (With Pipeline Validation)
- Real-time SteamCMD Download Progress & Validation Stream
- Resilient HTTP Resume Engine (4x Retries)
- Preview Scraper & JPG Converter
"""

# =====================================================================
# 1. AUTO-DEPENDENCY RESOLVER & SELF-INSTALLER (BOOTSTRAP)
# =====================================================================
import importlib
import subprocess
import sys
import time

REQUIRED_DEPENDENCIES = {
    "rich": "rich>=13.0.0",
    "requests": "requests>=2.28.0",
    "bs4": "beautifulsoup4>=4.11.0",
    "PIL": "Pillow>=9.0.0",
}

def bootstrap_dependencies() -> None:
    """Verifies and auto-installs missing Python packages before startup."""
    missing_packages = []
    for module_name, pip_spec in REQUIRED_DEPENDENCIES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing_packages.append((module_name, pip_spec))

    if missing_packages:
        print("\033[93m[*] Dependency Verification: Missing required packages detected.\033[0m")
        print("\033[96m[*] Auto-installing dependencies via pip...\033[0m")
        for module_name, pip_spec in missing_packages:
            print(f"  -> Installing {pip_spec}...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pip_spec],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.STDOUT,
                )
                print(f"  \033[92m✔ Successfully installed {module_name}\033[0m")
            except subprocess.CalledProcessError as err:
                print(f"\033[91m[!] Failed to install {pip_spec}: {err}\033[0m")
                sys.exit(1)
        print("\033[92m[*] All dependencies satisfied. Bootstrapping application...\033[0m\n")

bootstrap_dependencies()

# =====================================================================
# STANDARD & THIRD-PARTY IMPORTS (POST-BOOTSTRAP)
# =====================================================================
import datetime
import io
import json
import lzma
import os
import re
import shutil
import traceback
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from PIL import Image
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table

# =====================================================================
# CONSTANTS & CONFIGURATION
# =====================================================================
VERSION = "1.0.0"
STEAM_API_ENDPOINT = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
CONFIG_DIR = Path.home() / ".steam_workshop_downloader"
CONFIG_FILE = CONFIG_DIR / "config.json"
ERROR_LOG_FILE = Path("error_log.txt").resolve()

APP_NAMES = {
    4000: "Garry's Mod (GMod)",
    1840: "Source Filmmaker (SFM)",
}

# Regex for finding off-site cloud hosting links
EXTERNAL_CLOUD_REGEX = re.compile(
    r"(https?://(?:drive\.google\.com|docs\.google\.com/file|mega\.nz|mega\.co\.nz|mediafire\.com|www\.mediafire\.com|dropbox\.com|www\.dropbox\.com|anonfiles\.com|pixeldrain\.com|1drv\.ms|sharepoint\.com|modsfire\.com)[^\s\'\"<>]+)",
    re.IGNORECASE,
)

console = Console()

# =====================================================================
# ERROR LOGGING SYSTEM
# =====================================================================
def log_exception(context: str, exc: Exception) -> None:
    """Logs unhandled or critical exceptions to error_log.txt with traceback."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    error_type = type(exc).__name__
    stack_trace = traceback.format_exc()
    log_entry = (
        f"{'=' * 80}\n"
        f"TIMESTAMP  : {timestamp}\n"
        f"CONTEXT    : {context}\n"
        f"ERROR TYPE : {error_type}\n"
        f"MESSAGE    : {str(exc)}\n"
        f"TRACEBACK  :\n{stack_trace}\n"
        f"{'=' * 80}\n"
    )
    try:
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as io_err:
        console.print(f"[bold red]Failed to write to error log:[/bold red] {io_err}")

def show_error_panel(user_message: str, exc: Optional[Exception] = None) -> None:
    """Renders a user-friendly error panel and references the log file."""
    if exc:
        log_exception(user_message, exc)
    error_text = (
        f"[bold red]⚠ {user_message}[/bold red]\n"
        f"[dim]Details and full stack trace have been logged to:[/dim]\n"
        f"[cyan]{ERROR_LOG_FILE}[/cyan]"
    )
    console.print(
        Panel(
            error_text,
            title="[bold red]Operation Notice[/bold red]",
            border_style="red",
        )
    )

# =====================================================================
# CONFIGURATION MANAGER
# =====================================================================
@dataclass
class AppConfig:
    default_download_dir: str = str(Path.home() / "Downloads" / "SteamWorkshop")
    auto_zip: bool = False
    steamcmd_path: str = ""
    gmad_path: str = ""

    @classmethod
    def load(cls) -> "AppConfig":
        """Loads configuration from persistent JSON file."""
        if not CONFIG_FILE.exists():
            config = cls()
            config.save()
            return config
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Filter data to only include valid fields for AppConfig to prevent crashes on legacy configs
            valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
            filtered_data = {k: v for k, v in data.items() if k in valid_fields}
            return cls(**filtered_data)
        except Exception as e:
            log_exception("Loading Config File", e)
            return cls()

    def save(self) -> None:
        """Saves current configuration to persistent JSON file."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception as e:
            log_exception("Saving Config File", e)

# =====================================================================
# UTILITIES & CLOUD LINK DETECTOR
# =====================================================================
def detect_external_cloud_links(description: str) -> List[str]:
    """Scans item description for off-site cloud hosting links."""
    if not description:
        return []
    matches = EXTERNAL_CLOUD_REGEX.findall(description)
    unique_links = []
    for link in matches:
        clean_link = link.rstrip(".,;)>]").strip()
        if clean_link not in unique_links:
            unique_links.append(clean_link)
    return unique_links

def format_bytes(size: int) -> str:
    """Formats bytes into human-readable units (B, KB, MB, GB, TB)."""
    if size <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_idx = 0
    size_f = float(size)
    while size_f >= 1024.0 and unit_idx < len(units) - 1:
        size_f /= 1024.0
        unit_idx += 1
    return f"{size_f:.2f} {units[unit_idx]}" if unit_idx > 0 else f"{int(size_f)} B"

def sanitize_filename(filename: str) -> str:
    """Cleans names to be safe for cross-platform filesystems."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    return sanitized.strip().replace(" ", "_") or "workshop_item"

def extract_published_file_id(input_str: str) -> Optional[str]:
    """Extracts a PublishedFileId from a single Workshop URL or numeric ID."""
    input_str = input_str.strip()
    if input_str.isdigit():
        return input_str
    match = re.search(r"[?&]id=(\d+)", input_str)
    if match:
        return match.group(1)
    match = re.search(r"/(\d+)(?:/|$|\?)", input_str)
    if match:
        return match.group(1)
    return None

def is_profile_workshop_url(input_str: str) -> bool:
    """Detects whether the input string is a creator's workshop profile URL."""
    cleaned = input_str.lower().strip()
    return (
        "myworkshopfiles" in cleaned
        or "/workshop/browse" in cleaned
        or ("/profiles/" in cleaned and "workshop" in cleaned)
        or ("/id/" in cleaned and "workshop" in cleaned)
    )

def parse_selection_indices(selection_str: str, max_items: int) -> List[int]:
    """Parses selection queries (e.g. 'all', '1-5', '1, 4, 7', '2-6, 9')."""
    selection_str = selection_str.strip().lower()
    if selection_str == "all":
        return list(range(max_items))
    
    selected: Set[int] = set()
    tokens = [t.strip() for t in selection_str.split(",") if t.strip()]
    for token in tokens:
        if "-" in token:
            parts = token.split("-", 1)
            if parts[0].isdigit() and parts[1].isdigit():
                start, end = int(parts[0]), int(parts[1])
                if start > end:
                    start, end = end, start
                for idx in range(start, end + 1):
                    if 1 <= idx <= max_items:
                        selected.add(idx - 1)
        elif token.isdigit():
            idx = int(token)
            if 1 <= idx <= max_items:
                selected.add(idx - 1)
    return sorted(list(selected))

def locate_steamcmd(custom_path: str = "") -> Optional[str]:
    """Finds steamcmd executable on the host system."""
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
        if p.is_dir():
            possible = p / ("steamcmd.exe" if os.name == "nt" else "steamcmd.sh")
            if possible.is_file():
                return str(possible)
                
    found = shutil.which("steamcmd") or shutil.which("steamcmd.exe")
    if found:
        return found
        
    common_paths = [
        "C:\\steamcmd\\steamcmd.exe",
        "C:\\Program Files (x86)\\SteamCMD\\steamcmd.exe",
        os.path.expandvars("%LOCALAPPDATA%\\SteamCMD\\steamcmd.exe"),
        os.path.expanduser("~/.steam/steamcmd/steamcmd.sh"),
        os.path.expanduser("~/.local/share/Steam/steamcmd/steamcmd.sh"),
        "/usr/games/steamcmd",
        "/usr/bin/steamcmd",
    ]
    for cp in common_paths:
        if os.path.isfile(cp):
            return cp
    return None

def locate_gmad(custom_path: str = "") -> Optional[str]:
    """Finds gmad.exe executable on the host system."""
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        if p.is_file():
            return str(p)
        if p.is_dir():
            possible = p / ("gmad.exe" if os.name == "nt" else "gmad")
            if possible.is_file():
                return str(possible)
                
    found = shutil.which("gmad") or shutil.which("gmad.exe")
    if found:
        return found
        
    common_paths = [
        "C:\\Program Files (x86)\\Steam\\steamapps\\common\\GarrysMod\\bin\\gmad.exe",
        "C:\\Program Files\\Steam\\steamapps\\common\\GarrysMod\\bin\\gmad.exe",
        os.path.expandvars("%PROGRAMFILES(X86)%\\Steam\\steamapps\\common\\GarrysMod\\bin\\gmad.exe"),
        os.path.expandvars("%PROGRAMFILES%\\Steam\\steamapps\\common\\GarrysMod\\bin\\gmad.exe"),
        os.path.expanduser("~/.steam/steam/steamapps/common/GarrysMod/bin/gmad"),
        os.path.expanduser("~/.local/share/Steam/steamapps/common/GarrysMod/bin/gmad"),
    ]
    for cp in common_paths:
        if os.path.isfile(cp):
            return cp
    return None

# =====================================================================
# PREVIEW / THUMBNAIL SCRAPER & JPG CONVERTER
# =====================================================================
class PreviewDownloader:
    """Scrapes, downloads, and converts workshop previews to standard JPEG."""
    
    @staticmethod
    def extract_preview_urls(item_id: str, direct_thumbnail: Optional[str] = None) -> List[str]:
        """Scrapes item page to fetch all full-resolution screenshot/gallery URLs."""
        image_urls: List[str] = []
        if direct_thumbnail:
            image_urls.append(direct_thumbnail)

        item_page_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={item_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        try:
            response = requests.get(item_page_url, headers=headers, timeout=12)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                matches = re.findall(r"ShowEnlargedImagePreview\(\s*'([^']+)'", response.text)
                for match in matches:
                    if match not in image_urls:
                        image_urls.append(match)
                        
                for img in soup.find_all("img", class_="workshopItemPreviewImage"):
                    src = img.get("src")
                    if src and src not in image_urls:
                        image_urls.append(src)
                        
                main_preview = soup.find("img", id="previewImageMain") or soup.find("img", id="previewImage")
                if main_preview and main_preview.get("src"):
                    src = main_preview["src"]
                    if src not in image_urls:
                        image_urls.append(src)
        except Exception as e:
            log_exception(f"Scraping previews for Item {item_id}", e)

        cleaned_urls: List[str] = []
        for url in image_urls:
            clean_url = re.sub(r"\?imw=\d+&imh=\d+.*$", "", url)
            if clean_url not in cleaned_urls:
                cleaned_urls.append(clean_url)

        return cleaned_urls

    @staticmethod
    def download_and_convert_previews(
        urls: List[str], destination_dir: Path, item_title: str
    ) -> List[Path]:
        """Downloads images and converts them to standard .jpg format using Pillow."""
        saved_files: List[Path] = []
        if not urls:
            return saved_files

        previews_dir = destination_dir / "previews"
        previews_dir.mkdir(parents=True, exist_ok=True)
        headers = {"User-Agent": "Mozilla/5.0"}

        for idx, url in enumerate(urls, start=1):
            try:
                res = requests.get(url, headers=headers, timeout=15)
                if res.status_code == 200:
                    image_data = res.content
                    image = Image.open(io.BytesIO(image_data))
                    rgb_image = image.convert("RGB")
                    output_path = previews_dir / f"preview_{idx:02d}.jpg"
                    rgb_image.save(output_path, "JPEG", quality=95)
                    saved_files.append(output_path)
            except Exception as e:
                log_exception(f"Downloading preview {url} for {item_title}", e)

        return saved_files

# =====================================================================
# CREATOR PROFILE WORKSHOP SCANNER & WEB API CLIENT
# =====================================================================
class SteamWorkshopAPI:
    """Handles Steam Web API and Creator Profile web scraping."""
    
    @staticmethod
    def fetch_batch_details(file_ids: List[str]) -> List[Dict[str, Any]]:
        """Queries Steam Web API for multiple Workshop IDs in batches."""
        if not file_ids:
            return []
        all_results: List[Dict[str, Any]] = []
        chunk_size = 50
        headers = {"User-Agent": "SteamWorkshopDownloader/2.5"}

        for i in range(0, len(file_ids), chunk_size):
            chunk = file_ids[i : i + chunk_size]
            payload = {"itemcount": len(chunk)}
            for idx, fid in enumerate(chunk):
                payload[f"publishedfileids[{idx}]"] = fid

            try:
                response = requests.post(
                    STEAM_API_ENDPOINT, data=payload, headers=headers, timeout=20
                )
                response.raise_for_status()
                data = response.json()
                items = data.get("response", {}).get("publishedfiledetails", [])
                for item in items:
                    if item.get("result") == 1:
                        all_results.append(item)
            except Exception as e:
                log_exception(f"Batch API details fetch (chunk offset {i})", e)

        return all_results

    @staticmethod
    def get_single_item_details(item_id: str) -> Dict[str, Any]:
        """Fetches metadata for a single item ID."""
        results = SteamWorkshopAPI.fetch_batch_details([item_id])
        if not results:
            raise ValueError(
                f"Item {item_id} not accessible. It may be private, hidden, or deleted."
            )
        return results[0]

    @staticmethod
    def crawl_creator_profile(profile_url: str) -> Tuple[str, List[str]]:
        """Crawls a creator's workshop pages to extract creator name and all published file IDs."""
        parsed = urlparse(profile_url)
        base_query = parse_qs(parsed.query)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        collected_ids: List[str] = []
        author_name = "Creator"
        page = 1

        with console.status("[bold cyan]Crawling workshop pages...[/bold cyan]", spinner="dots"):
            while True:
                page_query = base_query.copy()
                page_query["p"] = [str(page)]
                page_query["numperpage"] = ["30"]
                new_parts = list(parsed)
                new_parts[4] = urlencode(page_query, doseq=True)
                page_url = urlunparse(new_parts)

                try:
                    res = requests.get(page_url, headers=headers, timeout=15)
                    if res.status_code != 200:
                        break
                    
                    soup = BeautifulSoup(res.text, "html.parser")
                    name_elem = soup.find("span", class_="actual_persona_name") or soup.find(
                        "div", class_="workshopHeaderTitle"
                    )
                    if name_elem and author_name == "Creator":
                        author_name = name_elem.get_text(strip=True)

                    links = soup.find_all("a", href=re.compile(r"id=(\d+)"))
                    page_ids: List[str] = []
                    for a in links:
                        href = a.get("href", "")
                        match = re.search(r"[?&]id=(\d+)", href)
                        if match:
                            fid = match.group(1)
                            if fid not in collected_ids and fid not in page_ids:
                                page_ids.append(fid)

                    if not page_ids:
                        break
                    
                    collected_ids.extend(page_ids)

                    has_next = False
                    for page_btn in soup.find_all("a", class_="pagebtn"):
                        if ">" in page_btn.get_text():
                            has_next = True
                            break
                            
                    if not has_next or page >= 50:
                        break
                    page += 1
                except Exception as e:
                    log_exception(f"Crawling workshop profile page {page}: {profile_url}", e)
                    break

        return author_name, collected_ids

# =====================================================================
# DOWNLOAD ENGINE (RESILIENT STREAMING, LZMA DECOMP & STEAMCMD PROGRESS)
# =====================================================================
class WorkshopDownloadManager:
    """Manages file downloads via Resilient Direct HTTP, LZMA Decompression, or SteamCMD."""
    
    def __init__(self, config: AppConfig):
        self.config = config

    def ensure_steamcmd_executable(self) -> Optional[str]:
        """Ensures SteamCMD is available or interactively prompts and saves its path."""
        steamcmd_exe = locate_steamcmd(self.config.steamcmd_path)
        if steamcmd_exe:
            return steamcmd_exe

        console.print(
            Panel(
                "[bold yellow]SteamCMD Required[/bold yellow]\n"
                "This item requires SteamCMD because Steam does not provide a direct CDN link.\n"
                "SteamCMD was not found in standard system locations.",
                border_style="yellow",
            )
        )
        while True:
            entered_path = Prompt.ask(
                "[bold cyan]Enter the full path to steamcmd[/bold cyan] (e.g. [yellow]C:\\steamcmd\\steamcmd.exe[/yellow] or '[bold red]c[/bold red]' to cancel)"
            ).strip()
            if entered_path.lower() in ("c", "cancel", "q", "quit"):
                return None
            
            validated = locate_steamcmd(entered_path)
            if validated:
                self.config.steamcmd_path = validated
                self.config.save()
                console.print(f"[bold green]✔ SteamCMD located and saved to config:[/bold green] [cyan]{validated}[/cyan]\n")
                return validated
            else:
                console.print("[bold red]❌ Invalid path or executable not found.[/bold red] Please try again.\n")

    def ensure_gmad_executable(self) -> Optional[str]:
        """Ensures gmad.exe is available or interactively prompts and saves its path."""
        gmad_exe = locate_gmad(self.config.gmad_path)
        if gmad_exe:
            return gmad_exe

        console.print(
            Panel(
                "[bold yellow]gmad.exe Required[/bold yellow]\n"
                "To extract .gma files, gmad.exe is required.\n"
                "It was not found in standard Garry's Mod installation paths.",
                border_style="yellow",
            )
        )
        while True:
            entered_path = Prompt.ask(
                "[bold cyan]Enter the full path to gmad.exe[/bold cyan] (e.g. [yellow]C:\\...\\gmad.exe[/yellow] or '[bold red]c[/bold red]' to cancel)"
            ).strip()
            if entered_path.lower() in ("c", "cancel", "q", "quit"):
                return None
            
            validated = locate_gmad(entered_path)
            if validated:
                self.config.gmad_path = validated
                self.config.save()
                console.print(f"[bold green]✔ gmad.exe located and saved to config:[/bold green] [cyan]{validated}[/cyan]\n")
                return validated
            else:
                console.print("[bold red]❌ Invalid path or executable not found.[/bold red] Please try again.\n")

    def decompress_gma_lzma(self, file_path: Path) -> bool:
        """
        Checks if a .gma file is LZMA compressed and decompresses it in-place.
        Returns True if successful or already a raw GMAD, False if decompression failed.
        """
        if file_path.suffix.lower() != ".gma":
            return False
        
        temp_path = file_path.with_suffix(".gma.decomp")
        
        # Ensure temp file doesn't exist from a previous crashed run
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass

        try:
            # 1. Check original header
            with open(file_path, "rb") as f:
                header = f.read(4)
                if header == b"GMAD":
                    console.print("[dim]GMA file is already uncompressed (GMAD header found).[/dim]")
                    return True
            
            console.print("[bold yellow]⚠ GMA file is LZMA compressed. Decompressing in-place...[/bold yellow]")
            
            # 2. Stream decompression (Explicit isolated blocks to prevent WinError 32)
            with lzma.open(file_path, "rb") as f_lzma, open(temp_path, "wb") as f_out:
                while True:
                    chunk = f_lzma.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    f_out.write(chunk)
            
            # 3. Verify header of decompressed file
            is_valid = False
            with open(temp_path, "rb") as f_check:
                if f_check.read(4) == b"GMAD":
                    is_valid = True
            
            if is_valid:
                # All file handles are guaranteed closed here due to 'with' blocks
                os.replace(temp_path, file_path)
                console.print("[bold green]✔ Successfully decompressed and verified GMA file.[/bold green]")
                return True
            else:
                console.print("[bold red]❌ Decompressed data does not start with GMAD header. Aborting overwrite.[/bold red]")
                return False
                
        except Exception as e:
            log_exception(f"LZMA Decompression failed for {file_path}", e)
            return False
        finally:
            # Clean up temp file if it still exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def extract_gma_file(self, gma_path: Path, output_dir: Path) -> bool:
        """Extracts a .gma file using gmad.exe."""
        # Pipeline Validation: Verify GMA header before attempting extraction
        try:
            with open(gma_path, "rb") as f:
                header = f.read(4)
                if header != b"GMAD":
                    console.print(f"[bold red]❌ GMA file {gma_path.name} is not valid (missing GMAD header). Skipping extraction.[/bold red]")
                    return False
        except Exception as e:
            log_exception(f"Failed to read GMA header for {gma_path}", e)
            return False

        gmad_exe = self.ensure_gmad_executable()
        if not gmad_exe:
            return False
        
        output_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            gmad_exe,
            "extract",
            "-file", str(gma_path),
            "-out", str(output_dir)
        ]
        
        console.print(f"[bold cyan]Extracting {gma_path.name} using gmad.exe...[/bold cyan]")
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            console.print("[bold green]✔ GMA extraction completed successfully.[/bold green]")
            return True
        except subprocess.CalledProcessError as e:
            log_exception(f"gmad.exe extraction failed for {gma_path}", Exception(f"STDERR: {e.stderr}\nSTDOUT: {e.stdout}"))
            console.print(f"[bold red]❌ GMA extraction failed. Check error_log.txt for details.[/bold red]")
            return False
        except Exception as e:
            log_exception(f"gmad.exe execution error for {gma_path}", e)
            return False

    def download_direct_http(
        self, file_url: str, output_filepath: Path, expected_size: int, max_retries: int = 4
    ) -> bool:
        """Streams direct HTTP download with auto-resume and retry logic."""
        total_size = expected_size
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading...", total=total_size if total_size > 0 else None)

            for attempt in range(1, max_retries + 2):
                existing_bytes = output_filepath.stat().st_size if output_filepath.exists() else 0
                
                if total_size > 0 and existing_bytes >= total_size:
                    progress.update(task, completed=total_size)
                    return True

                headers = {
                    "User-Agent": "SteamWorkshopDownloader/2.5",
                    "Accept-Encoding": "identity",
                }
                if existing_bytes > 0:
                    headers["Range"] = f"bytes={existing_bytes}-"
                    progress.update(task, completed=existing_bytes)

                try:
                    with requests.get(file_url, headers=headers, stream=True, timeout=(15, 60)) as r:
                        if r.status_code == 416:
                            return True
                        if r.status_code not in (200, 206):
                            r.raise_for_status()

                        content_length = r.headers.get("Content-Length")
                        if content_length:
                            if r.status_code == 200:
                                total_size = int(content_length)
                                existing_bytes = 0
                            elif r.status_code == 206:
                                total_size = existing_bytes + int(content_length)
                            progress.update(task, total=total_size)

                        mode = "ab" if r.status_code == 206 else "wb"
                        with open(output_filepath, mode) as f:
                            for chunk in r.iter_content(chunk_size=131072):
                                if chunk:
                                    f.write(chunk)
                                    progress.update(task, advance=len(chunk))

                        final_size = output_filepath.stat().st_size if output_filepath.exists() else 0
                        if total_size > 0 and final_size < total_size:
                            raise requests.exceptions.ChunkedEncodingError(
                                f"Downloaded {final_size} bytes, expected {total_size} bytes."
                            )
                        
                        return True

                except (
                    requests.exceptions.RequestException,
                    requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    Exception,
                ) as exc:
                    log_exception(f"Direct download attempt {attempt}/{max_retries + 1} failed: {file_url}", exc)
                    if attempt <= max_retries:
                        current_got = output_filepath.stat().st_size if output_filepath.exists() else 0
                        console.print(
                            f"\n[bold yellow]⚠ Connection interrupted ({type(exc).__name__}). "
                            f"Resuming download from {format_bytes(current_got)} (Attempt {attempt}/{max_retries})...[/bold yellow]"
                        )
                        time.sleep(2 * attempt)
                    else:
                        console.print(f"\n[bold red]❌ Direct download failed after {max_retries + 1} attempts.[/bold red]")
                        return False
        return False

    def download_via_steamcmd(
        self, app_id: int, item_id: str, destination_dir: Path
    ) -> Optional[Path]:
        """Downloads workshop item via SteamCMD with rich real-time stdout tracking."""
        steamcmd_exe = self.ensure_steamcmd_executable()
        if not steamcmd_exe:
            return None

        cmd = [
            steamcmd_exe,
            "+@ShutdownOnFailedCommand", "1",
            "+@NoPromptForPassword", "1",
            "+login", "anonymous",
            "+workshop_download_item", str(app_id), str(item_id), "validate",
            "+quit",
        ]

        console.print(f"[dim]Initiating SteamCMD download via: {steamcmd_exe}[/dim]")
        
        progress_pattern = re.compile(
            r"Update state \((?P<state>0x[0-9a-fA-F]+)\)\s+(?P<stage>[a-zA-Z]+),\s+progress:\s+(?P<pct>[\d\.]+)(?:\s*\(\s*(?P<cur>\d+)\s*/\s*(?P<tot>\d+)\s*\))?"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            "•",
            DownloadColumn(),
            "•",
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[bold cyan]Connecting to Steam Network...", total=100)

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )
                
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ""):
                        clean_line = line.strip()
                        if not clean_line:
                            continue

                        match = progress_pattern.search(clean_line)
                        if match:
                            stage = match.group("stage").capitalize()
                            pct = float(match.group("pct"))
                            cur_b = int(match.group("cur")) if match.group("cur") else None
                            tot_b = int(match.group("tot")) if match.group("tot") else None
                            
                            desc = f"[bold cyan]SteamCMD: {stage}..."
                            if cur_b is not None and tot_b is not None:
                                progress.update(
                                    task,
                                    completed=cur_b,
                                    total=tot_b,
                                    description=desc,
                                )
                            else:
                                progress.update(
                                    task,
                                    completed=pct,
                                    total=100,
                                    description=desc,
                                )
                        elif "logging in" in clean_line.lower():
                            progress.update(task, description="[bold cyan]Logging in anonymously...")
                        elif "success" in clean_line.lower() and "downloaded" in clean_line.lower():
                            progress.update(task, description="[bold green]Download finished! Finalizing...", completed=100)
                
                proc.wait()
            except Exception as e:
                log_exception(f"SteamCMD execution failed for Item {item_id}", e)
                return None

        steamcmd_root = Path(steamcmd_exe).parent
        download_location = (
            steamcmd_root
            / "steamapps"
            / "workshop"
            / "content"
            / str(app_id)
            / str(item_id)
        )

        if not download_location.exists():
            alt_loc = (
                Path.cwd()
                / "steamapps"
                / "workshop"
                / "content"
                / str(app_id)
                / str(item_id)
            )
            if alt_loc.exists():
                download_location = alt_loc
            else:
                return None

        target_item_dir = destination_dir / f"workshop_{item_id}"
        target_item_dir.mkdir(parents=True, exist_ok=True)

        for item in download_location.iterdir():
            dest = target_item_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        return target_item_dir

    @staticmethod
    def compress_bundle_to_zip(
        main_file_or_dir: Path, previews: List[Path], output_zip_path: Path
    ) -> Path:
        """Compresses workshop content and preview images into a .zip archive."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Compressing into ZIP archive..."),
            console=console,
        ) as progress:
            task = progress.add_task("Zipping", total=None)
            with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                if main_file_or_dir.is_file():
                    zipf.write(main_file_or_dir, arcname=main_file_or_dir.name)
                elif main_file_or_dir.is_dir():
                    for root, _, files in os.walk(main_file_or_dir):
                        for file in files:
                            full_path = Path(root) / file
                            arcname = full_path.relative_to(main_file_or_dir)
                            zipf.write(full_path, arcname=str(arcname))
                
                for preview in previews:
                    if preview.exists():
                        zipf.write(preview, arcname=f"previews/{preview.name}")
            progress.update(task, completed=1)
        return output_zip_path

# =====================================================================
# TERMINAL USER INTERFACE
# =====================================================================
class TerminalUI:
    """Rich TUI elements, tables, banners, and layout renderers."""
    
    @staticmethod
    def render_banner() -> None:
        """Renders stylized ASCII title banner."""
        banner_text = """
[bold cyan]███████╗████████╗███████╗ █████╗ ███╗   ███╗[/bold cyan] [bold white]██╗    ██╗ ██████╗ ██████╗ ██╗  ██╗[/bold white]
[bold cyan]██╔════╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║[/bold cyan] [bold white]██║    ██║██╔═══██╗██╔══██╗██║ ██╔╝[/bold white]
[bold cyan]███████╗   ██║   █████╗  ███████║██╔████╔██║[/bold cyan] [bold white]██║ █╗ ██║██║   ██║██████╔╝█████╔╝ [/bold white]
[bold cyan]╚════██║   ██║   ██╔══╝  ██╔══██║██║╚██╔╝██║[/bold cyan] [bold white]██║███╗██║██║   ██║██╔══██╗██╔═██╗ [/bold white]
[bold cyan]███████║   ██║   ███████╗██║  ██║██║ ╚═╝ ██║[/bold cyan] [bold white]╚███╔███╔╝╚██████╔╝██║  ██║██║  ██╗[/bold white]
[bold cyan]╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝[/bold cyan] [bold white] ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝[/bold white]
"""
        subtitle = (
            f"[bold yellow]Garry's Mod & SFM Workshop Suite[/bold yellow] | "
            f"[bold green]v{VERSION}[/bold green] (Public steam workshop downloader)"
        )
        panel = Panel(
            Align.center(f"{banner_text}\n{subtitle}"),
            border_style="bright_blue",
            padding=(0, 1),
        )
        console.print(panel)

    @staticmethod
    def render_external_links_panel(links: List[str]) -> None:
        """Renders prominent notice when off-site cloud download links are detected."""
        links_formatted = "\n".join([f"  [bold yellow]•[/bold yellow] [underline cyan]{l}[/underline cyan]" for l in links])
        notice_text = (
            "[bold red]⚠ EXTERNAL DOWNLOAD REQUIRED (Off-site Model/Addon)[/bold red]\n"
            "The author included external cloud hosting links in the item description.\n"
            "Usually, this means the main asset is too large for Workshop and [bold white]must be downloaded manually[/bold white] from:\n"
            f"{links_formatted}\n"
            "[dim]Note: The file downloaded from Steam might only be a small placeholder or texture base.[/dim]"
        )
        console.print(Panel(notice_text, title="[bold red]External Cloud Links Found[/bold red]", border_style="red"))

    @staticmethod
    def render_single_item_table(metadata: Dict[str, Any]) -> None:
        """Renders inspection table with single item details."""
        table = Table(
            title="[bold yellow]Workshop Item Inspection[/bold yellow]",
            show_header=True,
            header_style="bold magenta",
            border_style="cyan",
            expand=True,
        )
        table.add_column("Property", style="bold white", width=22)
        table.add_column("Value", style="green")

        title = metadata.get("title", "Unknown Title")
        item_id = str(metadata.get("publishedfileid", "Unknown"))
        app_id = int(metadata.get("consumer_app_id", 0))
        app_label = APP_NAMES.get(app_id, f"Other / Unknown (AppID: {app_id})")
        
        if app_id == 4000:
            app_styled = f"[bold cyan]{app_label}[/bold cyan]"
        elif app_id == 1840:
            app_styled = f"[bold yellow]{app_label}[/bold yellow]"
        else:
            app_styled = f"[bold red]{app_label}[/bold red]"

        file_size_raw = int(metadata.get("file_size", 0))
        file_size_fmt = (
            format_bytes(file_size_raw) if file_size_raw > 0 else "Dynamic / Cloud-hosted"
        )
        
        creator_id = metadata.get("creator", "Unknown")
        updated_epoch = metadata.get("time_updated", 0)
        updated_fmt = (
            datetime.datetime.fromtimestamp(
                updated_epoch, tz=datetime.timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S UTC")
            if updated_epoch
            else "Unknown"
        )
        
        has_direct_url = bool(metadata.get("file_url"))
        download_engine = (
            "[bold green]Direct Steam CDN (Fast + Auto-Resume)[/bold green]"
            if has_direct_url
            else "[bold yellow]SteamCMD Backend (Live Progress)[/bold yellow]"
        )

        table.add_row("Title", title)
        table.add_row("Workshop Item ID", item_id)
        table.add_row("Target Game", app_styled)
        table.add_row("File Size", file_size_fmt)
        table.add_row("Creator ID (Steam64)", str(creator_id))
        table.add_row("Last Updated", updated_fmt)
        table.add_row("Download Engine", download_engine)
        console.print(table)

    @staticmethod
    def render_creator_table(
        creator_name: str, items: List[Dict[str, Any]]
    ) -> Tuple[Table, int, Dict[str, List[str]]]:
        """Renders creator workshop items in a structured numbered table with cloud link indicators."""
        table = Table(
            title=f"[bold yellow]Creator Workshop: {creator_name} ({len(items)} Items Found)[/bold yellow]",
            show_header=True,
            header_style="bold magenta",
            border_style="cyan",
            expand=True,
        )
        table.add_column("#", style="bold cyan", width=5, justify="center")
        table.add_column("Item Title", style="bold white", min_width=28)
        table.add_column("Item ID", style="dim", width=12)
        table.add_column("Game / Type", style="green", width=18)
        table.add_column("File Size", style="yellow", justify="right", width=12)
        table.add_column("Status / Links", justify="center", width=18)

        combined_size = 0
        items_with_links: Dict[str, List[str]] = {}

        for idx, item in enumerate(items, start=1):
            raw_size = int(item.get("file_size", 0))
            combined_size += raw_size
            app_id = int(item.get("consumer_app_id", 0))
            app_str = APP_NAMES.get(app_id, f"AppID {app_id}")
            title = item.get("title", "Untitled")
            if len(title) > 38:
                title = title[:35] + "..."

            desc = item.get("description", "")
            ext_links = detect_external_cloud_links(desc)
            fid = str(item.get("publishedfileid"))
            
            if ext_links:
                items_with_links[fid] = ext_links
                status_str = "[bold red]⚠ Off-site Link[/bold red]"
            else:
                status_str = "[bold green]Ready[/bold green]"

            table.add_row(
                str(idx),
                title,
                fid,
                app_str,
                format_bytes(raw_size) if raw_size > 0 else "N/A",
                status_str,
            )

        return table, combined_size, items_with_links

# =====================================================================
# MAIN APPLICATION CONTROLLER
# =====================================================================
class WorkshopDownloaderApp:
    """Core interactive application loop and workflow engine."""
    
    def __init__(self):
        self.config = AppConfig.load()
        self.download_manager = WorkshopDownloadManager(self.config)

    def prompt_directory(self) -> Path:
        """Prompts for target directory with persistent default option."""
        current_default = self.config.default_download_dir
        console.print(f"\n[dim]Current default path: [white]{current_default}[/white][/dim]")
        chosen = Prompt.ask(
            "[bold cyan]Enter download path[/bold cyan] (Press [bold yellow]Enter[/bold yellow] to use default)",
            default=current_default,
            show_default=False,
        ).strip()
        
        target_path = Path(chosen).expanduser().resolve()
        target_path.mkdir(parents=True, exist_ok=True)
        
        if str(target_path) != current_default:
            save_default = Confirm.ask(
                f"Set '[cyan]{target_path}[/cyan]' as your persistent default download directory?",
                default=False,
            )
            if save_default:
                self.config.default_download_dir = str(target_path)
                self.config.save()
                console.print("[green]✔ Default directory updated in config.json![/green]")
        return target_path

    def download_item_pipeline(
        self,
        details: Dict[str, Any],
        target_dir: Path,
        download_previews: bool,
        should_zip: bool,
        auto_extract: bool = False,
    ) -> Optional[Path]:
        """Runs the complete download, decompression, extraction, and archiving pipeline."""
        item_id = str(details.get("publishedfileid"))
        title = sanitize_filename(details.get("title", f"item_{item_id}"))
        app_id = int(details.get("consumer_app_id", 0))
        direct_url = details.get("file_url")
        file_size = int(details.get("file_size", 0))

        item_workspace = target_dir / f"{title}_{item_id}"
        item_workspace.mkdir(parents=True, exist_ok=True)

        # 1. Download Item Payload
        downloaded_payload: Optional[Path] = None
        if direct_url:
            ext = ".gma" if app_id == 4000 else ".zip"
            dest_file = item_workspace / f"{title}{ext}"
            console.print(f"\n[bold green]⬇ Downloading payload:[/bold green] {dest_file.name}")
            
            success = self.download_manager.download_direct_http(
                direct_url, dest_file, file_size, max_retries=4
            )
            if success:
                downloaded_payload = dest_file
                
                # AUTOMATIC LZMA DECOMPRESSION FOR GMA FILES
                if ext == ".gma":
                    decomp_success = self.download_manager.decompress_gma_lzma(downloaded_payload)
                    if not decomp_success:
                        console.print("[bold red]❌ GMA Decompression failed. Skipping auto-extraction to prevent gmad.exe errors.[/bold red]")
            else:
                console.print(
                    "\n[yellow]Direct link unavailable from Steam API. Using SteamCMD backend...[/yellow]"
                )
                downloaded_payload = self.download_manager.download_via_steamcmd(
                    app_id, item_id, item_workspace
                )
        else:
            console.print(
                "\n[yellow]Direct link unavailable from Steam API. Using SteamCMD backend...[/yellow]"
            )
            downloaded_payload = self.download_manager.download_via_steamcmd(
                app_id, item_id, item_workspace
            )

        if not downloaded_payload or not downloaded_payload.exists():
            show_error_panel(f"Download failed for {title} (ID: {item_id}).")
            return None

        # 2. Auto-Extract .gma if requested
        if auto_extract and downloaded_payload.suffix.lower() == ".gma":
            extract_dir = item_workspace / f"{title}_extracted"
            console.print(f"\n[bold magenta]Auto-Extracting .gma payload...[/bold magenta]")
            
            # Pipeline Validation: Verify GMAD header before attempting extraction
            is_valid_gma = False
            try:
                with open(downloaded_payload, "rb") as f:
                    if f.read(4) == b"GMAD":
                        is_valid_gma = True
            except Exception as e:
                log_exception(f"Failed to read GMA header for pipeline validation: {downloaded_payload}", e)

            if is_valid_gma:
                if self.download_manager.extract_gma_file(downloaded_payload, extract_dir):
                    downloaded_payload = extract_dir
                else:
                    console.print("[yellow]Extraction failed. Proceeding with raw .gma file.[/yellow]")
            else:
                console.print("[bold red]❌ GMA file is invalid or still compressed. Skipping gmad.exe extraction to prevent parsing errors.[/bold red]")

        # 3. Preview & Gallery Images
        saved_previews: List[Path] = []
        if download_previews:
            console.print("[bold cyan]Fetching and converting preview gallery...[/bold cyan]")
            preview_urls = PreviewDownloader.extract_preview_urls(
                item_id, direct_thumbnail=details.get("preview_url")
            )
            saved_previews = PreviewDownloader.download_and_convert_previews(
                preview_urls, item_workspace, title
            )
            console.print(
                f"[green]✔ Saved {len(saved_previews)} preview image(s) as .jpg[/green]"
            )

        # 4. Post-Processing / Archiving
        final_destination: Path = item_workspace
        if should_zip:
            zip_dest = target_dir / f"{title}_{item_id}.zip"
            final_destination = self.download_manager.compress_bundle_to_zip(
                downloaded_payload, saved_previews, zip_dest
            )
            shutil.rmtree(item_workspace, ignore_errors=True)

        return final_destination

    def process_single_item(self, item_id: str) -> None:
        """Single workshop item download workflow with cloud link detection."""
        with console.status("[bold cyan]Fetching item metadata from Steam...[/bold cyan]", spinner="dots"):
            try:
                details = SteamWorkshopAPI.get_single_item_details(item_id)
            except Exception as e:
                show_error_panel(f"Failed to fetch item details for ID {item_id}", e)
                return

        TerminalUI.render_single_item_table(details)

        description = details.get("description", "")
        external_links = detect_external_cloud_links(description)
        if external_links:
            TerminalUI.render_external_links_panel(external_links)

        if not Confirm.ask("\n[bold cyan]Proceed with download?[/bold cyan]", default=True):
            console.print("[yellow]Download aborted by user.[/yellow]")
            return

        auto_extract = Confirm.ask(
            "[bold cyan]Do you want to automatically unpack/extract .gma files after downloading?[/bold cyan]",
            default=False,
        )

        want_previews = Confirm.ask(
            "[bold cyan]Do you want to download preview images with this item?[/bold cyan]",
            default=True,
        )
        target_dir = self.prompt_directory()

        console.print("\n[bold]Output Format Selection:[/bold]")
        console.print("  [1] Keep raw files / folder structure")
        console.print("  [2] Compress into a unified .zip archive")
        format_choice = Prompt.ask("Select format option", choices=["1", "2"], default="1")
        should_zip = format_choice == "2"

        final_path = self.download_item_pipeline(
            details, target_dir, want_previews, should_zip, auto_extract
        )
        
        if final_path:
            console.print(
                Panel(
                    f"[bold green]✔ Item successfully downloaded and processed![/bold green]\n"
                    f"[bold white]Title:[/bold white] {details.get('title')}\n"
                    f"[bold white]Location:[/bold white] [cyan]{final_path}[/cyan]",
                    title="[bold green]Download Complete[/bold green]",
                    border_style="green",
                )
            )

    def process_creator_profile(self, profile_url: str) -> None:
        """Creator profile crawler and selective batch download workflow with link scanner."""
        try:
            author_name, file_ids = SteamWorkshopAPI.crawl_creator_profile(profile_url)
        except Exception as e:
            show_error_panel("Failed to crawl creator workshop profile.", e)
            return

        if not file_ids:
            console.print(
                "[bold yellow]No workshop items found or profile is set to private.[/bold yellow]"
            )
            return

        with console.status("[bold cyan]Retrieving metadata for all items...[/bold cyan]", spinner="dots"):
            items = SteamWorkshopAPI.fetch_batch_details(file_ids)
            if not items:
                show_error_panel("Could not retrieve metadata for creator items.")
                return

        table, total_size, items_with_links = TerminalUI.render_creator_table(author_name, items)
        console.print(table)
        console.print(
            f"[bold]Total Items:[/bold] [cyan]{len(items)}[/cyan] | "
            f"[bold]Combined Size:[/bold] [yellow]{format_bytes(total_size)}[/yellow]\n"
        )

        if items_with_links:
            console.print(
                f"[bold red]⚠ Notice:[/bold red] [yellow]{len(items_with_links)} item(s)[/yellow] contain external cloud links (Google Drive / Mega). "
                "Those items may require manual off-site downloading."
            )

        selection_query = Prompt.ask(
            "[bold green]Enter items to download[/bold green] (e.g., [bold cyan]all[/bold cyan], [bold cyan]1-3[/bold cyan], [bold cyan]1, 4, 7[/bold cyan], or '[bold red]q[/bold red]' to cancel)"
        ).strip()

        if selection_query.lower() in ("q", "quit", "cancel"):
            console.print("[yellow]Batch download cancelled.[/yellow]")
            return

        selected_indices = parse_selection_indices(selection_query, len(items))
        if not selected_indices:
            console.print("[bold red]❌ Invalid selection. No items matched.[/bold red]")
            return

        selected_items = [items[i] for i in selected_indices]
        console.print(f"\n[bold green]Queued {len(selected_items)} item(s) for batch download.[/bold green]")

        auto_extract = Confirm.ask(
            "[bold cyan]Do you want to automatically unpack/extract .gma files after downloading?[/bold cyan]",
            default=False,
        )

        want_previews = Confirm.ask(
            "[bold cyan]Download preview images for each queued item?[/bold cyan]",
            default=False,
        )
        target_dir = self.prompt_directory()

        console.print("\n[bold]Output Format Selection:[/bold]")
        console.print("  [1] Keep raw files / folder structure")
        console.print("  [2] Compress each item into individual .zip archives")
        format_choice = Prompt.ask("Select format option", choices=["1", "2"], default="1")
        should_zip = format_choice == "2"

        success_count = 0
        console.print(Rule("[bold magenta]Starting Batch Download Queue[/bold magenta]"))

        for idx, item in enumerate(selected_items, start=1):
            fid = str(item.get("publishedfileid"))
            desc = item.get("description", "")
            ext_links = detect_external_cloud_links(desc)

            console.print(
                f"\n[bold blue][Queue {idx}/{len(selected_items)}][/bold blue] "
                f"[bold white]{item.get('title')} (ID: {fid})[/bold white]"
            )
            if ext_links:
                TerminalUI.render_external_links_panel(ext_links)

            try:
                res = self.download_item_pipeline(
                    item, target_dir, want_previews, should_zip, auto_extract
                )
                if res:
                    success_count += 1
            except Exception as item_err:
                show_error_panel(f"Error processing item {fid}", item_err)

        console.print(
            Panel(
                f"[bold green]✔ Batch download finished![/bold green]\n"
                f"[bold white]Successfully Downloaded:[/bold white] {success_count}/{len(selected_items)}\n"
                f"[bold white]Destination Folder:[/bold white] [cyan]{target_dir}[/cyan]",
                title="[bold green]Batch Process Complete[/bold green]",
                border_style="green",
            )
        )

    def run(self) -> None:
        """Main continuous interactive execution loop."""
        os.system("cls" if os.name == "nt" else "clear")
        TerminalUI.render_banner()
        
        while True:
            try:
                console.print(Rule(style="dim"))
                user_input = Prompt.ask(
                    "[bold green]Enter Workshop / Profile URL or Item ID[/bold green] (or type '[bold red]q[/bold red]' to exit)"
                ).strip()

                if not user_input:
                    continue
                if user_input.lower() in ("q", "quit", "exit"):
                    console.print("\n[bold cyan]Thank you for using Steam Workshop Suite. Goodbye![/bold cyan]")
                    sys.exit(0)

                if is_profile_workshop_url(user_input):
                    self.process_creator_profile(user_input)
                else:
                    item_id = extract_published_file_id(user_input)
                    if item_id:
                        self.process_single_item(item_id)
                    else:
                        console.print(
                            "[bold red]❌ Invalid input.[/bold red] Please provide a valid Workshop item ID, Item URL, or Creator Workshop Profile URL."
                        )

            except KeyboardInterrupt:
                console.print("\n[bold yellow]Session interrupted by user. Exiting gracefully...[/bold yellow]")
                sys.exit(0)
            except Exception as err:
                show_error_panel("An unexpected top-level error occurred.", err)

# =====================================================================
# ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    app = WorkshopDownloaderApp()
    app.run()