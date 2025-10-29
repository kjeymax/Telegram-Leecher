import re
import logging
import subprocess
import os
import asyncio
from datetime import datetime

# --- Libtorrent Imports (New) ---
try:
    import libtorrent as lt
except ImportError:
    logging.warning("libtorrent is not installed. Torrent/Magnet downloads will not work.")
    lt = None
# --- End of Libtorrent Imports ---

from colab_leecher.utility.helper import sizeUnit, status_bar
from colab_leecher.utility.variables import BOT, Paths, Messages, BotTimes

# --- Tracker system setup (No changes needed here) ---
ARIA2_DIR = os.path.expanduser("~/.aria2")
TRACKER_FILES = [
    ("best_aria2.txt", "https://cf.trackerslist.com/best_aria2.txt"),
    ("all_aria2.txt", "https://cf.trackerslist.com/all_aria2.txt"),
    ("http_aria2.txt", "https://cf.trackerslist.com/http_aria2.txt"),
    ("nohttp_aria2.txt", "https://cf.trackerslist.com/nohttp_aria2.txt"),      
]

os.makedirs(ARIA2_DIR, exist_ok=True)
trackers = []
for fname, url in TRACKER_FILES:
    fpath = os.path.join(ARIA2_DIR, fname)
    if not os.path.exists(fpath):
        subprocess.run(["wget", "-O", fpath, url])
    try:
        with open(fpath, "r") as f:
            # We need to filter out empty strings
            trackers.extend([tracker.strip() for tracker in f.read().split('\n') if tracker.strip()])
    except Exception:
        pass
# Unique trackers
TRACKERS_LIST = list(set(trackers))


def is_torrent_or_magnet(link: str):
    return link.endswith(".torrent") or link.startswith("magnet:")


def parse_link_options(link: str):
    import shlex
    parts = shlex.split(link)
    url, headers, out = None, [], None
    i = 0
    while i < len(parts):
        part = parts[i]
        if part == "--header" and i + 1 < len(parts):
            headers.append(parts[i + 1]); i += 2
        elif part == "--out" and i + 1 < len(parts):
            out = parts[i + 1]; i += 2
        elif part.startswith("--"): i += 1
        else:
            if url is None: url = part
            i += 1
    return url, headers, out

# ⭐️ --- NEW: Libtorrent Downloader --- ⭐️
async def libtorrent_download(magnet_uri: str, save_path: str, num: int):
    if not lt:
        logging.error("Cannot start torrent download: libtorrent library is missing.")
        return

    # ⭐️ --- NEW: High-Performance Settings --- ⭐️
    settings = {
        'user_agent': f'qBittorrent/4.4.5',
        'listen_interfaces': '0.0.0.0:6881',
        'enable_dht': True,
        'enable_lsd': True,
        'enable_upnp': True,
        'enable_natpmp': True,
        'announce_to_all_tiers': True,
        'announce_to_all_trackers': True,
        'aio_threads': 4, # Asynchronous I/O threads
        'checking_mem_usage': 2048, # Use more RAM for checking pieces
        'connections_limit': 2000, # Allow more connections
        'unchoke_slots_limit': 50,
        'active_downloads': -1,
        'active_seeds': -1,
        'active_limit': -1,
    }
    ses = lt.session(settings)
    # ⭐️ --- END OF NEW SETTINGS --- ⭐️

    params = lt.parse_magnet_uri(magnet_uri)
    # Add trackers to the torrent
    for tracker in TRACKERS_LIST:
        params.trackers.append(tracker)

    params.save_path = save_path
    handle = ses.add_torrent(params)

    # --- Rest of the function remains the same ---
    BotTimes.task_start = datetime.now()
    start_time = datetime.now()
    file_name = "Fetching..."
    
    while not handle.status().is_seeding:
        s = handle.status()
        
        if file_name == "Fetching..." and s.name:
            file_name = s.name
            Messages.status_head = f"<b>📥 DOWNLOADING FROM » </b><i>🧲 Magnet Link {str(num).zfill(2)}</i>\n\n<b>🏷️ Name » </b><code>{file_name}</code>\n"

        progress = s.progress * 100
        total_size_bytes = s.total_wanted
        downloaded_bytes = s.total_done
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        speed_bps = s.download_rate # Use libtorrent's own speed calculation
        
        remaining_bytes = total_size_bytes - downloaded_bytes
        eta_seconds = remaining_bytes / speed_bps if speed_bps > 0 else 0
        eta = f"{int(eta_seconds)}s" if eta_seconds > 0 and eta_seconds != float('inf') else "∞"

        await status_bar(
            Messages.status_head,
            f"{sizeUnit(speed_bps)}/s",
            int(progress),
            eta,
            sizeUnit(downloaded_bytes),
            sizeUnit(total_size_bytes),
            "Libtorrent 🚀" # Changed icon to show it's the speedy version
        )
        await asyncio.sleep(2)

    logging.info(f"Libtorrent download completed for: {file_name}")

# ⭐️ --- MODIFIED: Main Downloader Function --- ⭐️
async def aria2_Download(link: str, num: int):
    url, headers, out = parse_link_options(link)
    if url is None:
        logging.error("No valid URL found in link")
        return

    # --- HYBRID LOGIC ---
    if is_torrent_or_magnet(url):
        # If it's a torrent/magnet, use the new powerful libtorrent downloader
        logging.info(f"Torrent/Magnet link detected. Using Libtorrent for: {url}")
        await libtorrent_download(url, Paths.down_path, num)
        return  # Stop execution here, as libtorrent handled it
    # --- END OF HYBRID LOGIC ---

    # --- Existing aria2c logic for normal HTTP/S links ---
    name_d = get_Aria2c_Name(url if out is None else out)
    BotTimes.task_start = datetime.now()
    Messages.status_head = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<b>🏷️ Name » </b><code>{name_d}</code>\n"

    command = [
        "aria2c", "-x16", "--seed-time=0", "--summary-interval=1",
        "--max-tries=3", "--console-log-level=notice", "-d", Paths.down_path,
    ]

    for h in headers: command += ["--header", h]
    if out: command += ["-o", out]
    command.append(url)

    logging.info(f"Running aria2c command: {' '.join(command)}")

    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    while True:
        output_bytes = await proc.stdout.readline()
        if not output_bytes:
            break
        output_str = output_bytes.decode('utf-8').strip()
        if output_str:
            logging.info(f"aria2c output: {output_str}")
            await on_output(output_str)

    await proc.wait()
    # (Error handling for aria2c can be improved here if needed)


def get_Aria2c_Name(link):
    if len(BOT.Options.custom_name) != 0:
        return BOT.Options.custom_name
    cmd = f'aria2c -x10 --dry-run --file-allocation=none "{link}"'
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True, check=True)
        stdout_str = result.stdout
        filename = stdout_str.split("complete: ")[-1].split("\n")[0]
        name = filename.split("/")[-1]
        return name if name else "UNKNOWN DOWNLOAD NAME"
    except (subprocess.CalledProcessError, IndexError, Exception) as e:
        logging.error(f"Could not get aria2c name: {e}")
        return "UNKNOWN DOWNLOAD NAME"


async def on_output(output: str):
    # This function is now only for aria2c output, but let's keep it for now
    total_size, progress_percentage, downloaded_bytes, eta = "0B", "0%", "0B", "0S"
    try:
        if "ETA:" in output:
            parts = output.split()
            total_size_raw = parts[1].split('/')[1]
            total_size = total_size_raw.split('(')[0]
            progress_percentage = parts[1][parts[1].find("(") + 1 : parts[1].find(")")]
            downloaded_bytes = parts[1].split('/')[0]
            eta = parts[4].split(':')[1][:-1]
    except Exception as e:
        logging.error(f"Couldn't parse aria2c info due to: {e}")
        return

    if total_size != "0B":
        percentage = int(re.findall(r'\d+', progress_percentage)[0])
        await status_bar(
            Messages.status_head,
            "Calculating...", # Speed calculation for aria2 can be improved
            percentage,
            eta,
            downloaded_bytes,
            total_size,
            "Aria2c 🧨",
        )
