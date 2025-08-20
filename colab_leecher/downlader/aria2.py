import re
import logging
import subprocess
import os
import sys
from datetime import datetime
from colab_leecher.utility.helper import sizeUnit, status_bar
from colab_leecher.utility.variables import BOT, Aria2c, Paths, Messages, BotTimes

# --- Tracker system setup ---
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
            trackers.append(f.read().replace('\n', ','))
    except Exception:
        pass
TRACKER_STRING = ",".join(trackers)


def is_torrent_or_magnet(link: str):
    return link.endswith(".torrent") or link.startswith("magnet:")


async def aria2_Download(link: str, num: int):
    global BotTimes, Messages
    name_d = get_Aria2c_Name(link)
    BotTimes.task_start = datetime.now()
    Messages.status_head = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<b>🏷️ Name » </b><code>{name_d}</code>\n"

    # Detect torrent/magnet and set optimal flags
    if is_torrent_or_magnet(link):
        command = [
            "aria2c",
            "--enable-dht=true",
            "--enable-peer-exchange=true",
            "--bt-enable-lpd=true",
            "--bt-max-peers=100",
            "--bt-request-peer-speed-limit=0",
            "--bt-tracker-connect-timeout=10",
            "--bt-tracker-interval=60",
            "--bt-tracker-timeout=10",
            "--max-connection-per-server=16",
            "--max-concurrent-downloads=5",
            "--seed-time=0",
            "--summary-interval=1",
            "--console-log-level=notice",
            f"--bt-tracker={TRACKER_STRING}",
            "-d",
            Paths.down_path,
            link,
        ]
    else:
        command = [
            "aria2c",
            "-x16",
            "--seed-time=0",
            "--summary-interval=1",
            "--max-tries=3",
            "--console-log-level=notice",
            "-d",
            Paths.down_path,
            link,
        ]

    # Run the command using subprocess.Popen
    proc = subprocess.Popen(
        command, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Read and print output in real-time
    while True:
        output = proc.stdout.readline()  # type: ignore
        if output == b"" and proc.poll() is not None:
            break
        if output:
            # sys.stdout.write(output.decode("utf-8"))
            # sys.stdout.flush()
            await on_output(output.decode("utf-8"))

    # Retrieve exit code and any error output
    exit_code = proc.wait()
    error_output = proc.stderr.read()  # type: ignore
    if exit_code != 0:
        if exit_code == 3:
            logging.error(f"The Resource was Not Found in {link}")
        elif exit_code == 9:
            logging.error(f"Not enough disk space available")
        elif exit_code == 24:
            logging.error(f"HTTP authorization failed.")
        else:
            logging.error(
                f"aria2c download failed with return code {exit_code} for {link}.\nError: {error_output}"
            )


def get_Aria2c_Name(link):
    if len(BOT.Options.custom_name) != 0:
        return BOT.Options.custom_name
    cmd = f'aria2c -x10 --dry-run --file-allocation=none "{link}"'
    result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)
    stdout_str = result.stdout.decode("utf-8")
    filename = stdout_str.split("complete: ")[-1].split("\n")[0]
    name = filename.split("/")[-1]
    if len(name) == 0:
        name = "UNKNOWN DOWNLOAD NAME"
    return name


async def on_output(output: str):
    # Ensure Aria2c.link_info is initialized
    if not hasattr(Aria2c, "link_info"):
        Aria2c.link_info = False
    total_size = "0B"
    progress_percentage = "0B"
    downloaded_bytes = "0B"
    eta = "0S"
    try:
        if "ETA:" in output:
            parts = output.split()
            total_size = parts[1].split("/")[1]
            total_size = total_size.split("(")[0]
            progress_percentage = parts[1][
                parts[1].find("(") + 1 : parts[1].find(")")
            ]
            downloaded_bytes = parts[1].split("/")[0]
            eta = parts[4].split(":")[1][:-1]
    except Exception as do:
        logging.error(f"Could't Get Info Due to: {do}")

    percentage = re.findall(r"\d+\.\d+|\d+", progress_percentage)[0]  # type: ignore
    down = re.findall(r"\d+\.\d+|\d+", downloaded_bytes)[0]  # type: ignore
    down_unit = re.findall(r"[a-zA-Z]+", downloaded_bytes)[0]
    if "G" in down_unit:
        spd = 3
    elif "M" in down_unit:
        spd = 2
    elif "K" in down_unit:
        spd = 1
    else:
        spd = 0

    elapsed_time_seconds = (datetime.now() - BotTimes.task_start).seconds

    if elapsed_time_seconds >= 270 and not Aria2c.link_info:
        logging.error("Failed to get download information ! Probably dead link 💀")
    # Only Do this if got Information
    if total_size != "0B":
        # Calculate download speed
        Aria2c.link_info = True
        current_speed = (float(down) * 1024**spd) / elapsed_time_seconds
        speed_string = f"{sizeUnit(current_speed)}/s"

        await status_bar(
            Messages.status_head,
            speed_string,
            int(percentage),
            eta,
            downloaded_bytes,
            total_size,
            "Aria2c 🧨",
        )
