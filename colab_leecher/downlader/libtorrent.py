# copyright 2024 © KavinduAJ | https://github.com/kjeymax

import logging
import asyncio
from datetime import datetime
import requests
import qbittorrentapi

from colab_leecher.utility.helper import sizeUnit, status_bar
from colab_leecher.utility.variables import BOT, Paths, Messages, BotTimes

QB_HOST = "localhost"
QB_PORT = 8080
QB_USERNAME = "admin"
QB_PASSWORD = "adminadmin"  # Change according to your config

TRACKER_URL = "https://cf.trackerslist.com/best.txt"

def fetch_trackers(url):
    """Download tracker list from a given URL and return as a list of strings."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        trackers = [
            line.strip() for line in response.text.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        return trackers
    except Exception as e:
        logging.error(f"Failed to fetch trackers from {url}: {e}")
        return []

async def qbittorrent_Download(link: str, num: int):
    global BotTimes, Messages
    name_d = await get_qbittorrent_Name(link)
    BotTimes.task_start = datetime.now()
    Messages.status_head = (
        f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n"
        f"<b>🏷️ Name » </b><code>{name_d}</code>\n"
    )

    # Download tracker list
    trackers = fetch_trackers(TRACKER_URL)

    # Connect to qBittorrent Web API
    client = qbittorrentapi.Client(
        host=f"http://{QB_HOST}:{QB_PORT}",
        username=QB_USERNAME,
        password=QB_PASSWORD
    )
    try:
        client.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        logging.error(f"qBittorrent login failed: {e}")
        return

    # Add torrent (magnet or .torrent)
    try:
        if link.startswith("magnet:"):
            client.torrents_add(urls=link, save_path=Paths.down_path)
        elif link.startswith(("http://", "https://")) and link.endswith(".torrent"):
            client.torrents_add(urls=link, save_path=Paths.down_path)
        else:
            logging.error("Unsupported URI protocol for qBittorrent.")
            return
    except Exception as e:
        logging.error(f"Failed to add torrent: {e}")
        return

    await on_download_started()

    # Wait for torrent to appear in qBittorrent’s list
    for _ in range(10):
        torrents = client.torrents_info()
        torrent = next((t for t in torrents if t.name == name_d), None)
        if torrent:
            break
        await asyncio.sleep(1)
    else:
        logging.error("Torrent not found in qBittorrent list.")
        return

    # Add all trackers to the torrent
    try:
        client.torrents_add_trackers(torrent_hash=torrent.hash, urls=trackers)
    except Exception as e:
        logging.error(f"Failed to add trackers: {e}")

    # Main download loop
    while torrent.state != "uploading" and torrent.progress < 1:
        await on_download_progress_qbt(torrent)

        # Refresh torrent info
        await asyncio.sleep(1)
        torrents = client.torrents_info()
        torrent = next((t for t in torrents if t.name == name_d), torrent)

    await on_download_complete()
    logging.info("Stay Tuned ⌛️")

async def get_qbittorrent_Name(link):
    # qBittorrent does not provide name before adding, so use custom name or fallback
    if len(BOT.Options.custom_name) != 0:
        return BOT.Options.custom_name
    # Try to extract name from magnet link (if possible)
    if link.startswith("magnet:"):
        import re
        m = re.search("dn=([^&]+)", link)
        return m.group(1) if m else "Unknown Download Name 🤷‍♂️"
    elif link.endswith(".torrent"):
        return link.split("/")[-1].replace(".torrent", "")
    return "Unknown Download Name 🤷‍♂️"

async def on_download_started():
    logging.info("Download started 😀")

async def on_download_progress_qbt(torrent):
    total_size = torrent.size
    downloaded_bytes = int(torrent.progress * total_size)
    progress_percentage = torrent.progress * 100 if total_size != 0 else 0
    eta = torrent.eta if hasattr(torrent, "eta") else 0
    current_speed = torrent.dlspeed
    speed_string = f"{sizeUnit(current_speed)}/s"

    # Convert total size and downloaded bytes to human-readable format
    total_size_hr = sizeUnit(total_size)
    downloaded_bytes_hr = sizeUnit(downloaded_bytes)

    await status_bar(
        Messages.status_head,
        speed_string,
        int(progress_percentage),
        eta,
        downloaded_bytes_hr,
        total_size_hr,
        "QBT 🧲",
    )

def sizeUnit(size):
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"

async def on_download_complete():
    logging.info("Download complete ✅")
    # Add any additional actions you want to perform after download completion here
