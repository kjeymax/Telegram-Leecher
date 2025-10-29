#https://github.com/kjeymax

import logging
from natsort import natsorted
from datetime import datetime
from asyncio import sleep

from colab_leecher.downlader.mega import megadl
from colab_leecher.utility.handler import cancelTask
from colab_leecher.downlader.ytdl import YTDL_Status, get_YT_Name
from colab_leecher.downlader.aria2 import aria2_Download, get_Aria2c_Name
from colab_leecher.utility.helper import isYtdlComplete, keyboard, sysINFO
from colab_leecher.downlader.telegram import TelegramDownload, media_Identifier
from colab_leecher.utility.variables import BOT, Transfer, MSG, Messages, BotTimes
from colab_leecher.downlader.gdrive import (
    build_service,
    g_DownLoad,
    get_Gfolder_size,
    getFileMetadata,
    getIDFromURL,
)


async def downloadManager(sources, is_ytdl: bool):
    message = "\n<b>Please Wait...</b> ⏳\n<i>Merging YTDL Video...</i> 🐬"
    BotTimes.task_start = datetime.now()
    if is_ytdl:
        for i, link in enumerate(sources):
            await YTDL_Status(link, i + 1)
        try:
            await MSG.status_msg.edit_text(
                text=Messages.task_msg + Messages.status_head + message + sysINFO(),
                reply_markup=keyboard(),
            )
        except Exception as e:
            logging.error(f"Error updating message: {e}")
        while not isYtdlComplete():
            await sleep(2)
    else:
        for i, link in enumerate(sources):
            try:
                if "drive.google.com" in link:
                    await g_DownLoad(link, i + 1)
                elif "t.me" in link:
                    await TelegramDownload(link, i + 1)
                elif "youtube.com" in link or "youtu.be" in link:
                    await YTDL_Status(link, i + 1)
                    try:
                        await MSG.status_msg.edit_text(
                            text=Messages.task_msg
                            + Messages.status_head
                            + message
                            + sysINFO(),
                            reply_markup=keyboard(),
                        )
                    except Exception as e:
                        logging.error(f"Error updating message: {e}")
                    while not isYtdlComplete():
                        await sleep(2)
                elif "mega.nz" in link:
                    await megadl(link, i + 1)
                else:
                    await aria2_Download(link, i + 1)
            except Exception as Error:
                logging.error(f"Error While Downloading: {Error}", exc_info=True)
                await cancelTask(f"Download Error: {str(Error)}")
                return


async def calDownSize(sources):
    for link in natsorted(sources):
        if "drive.google.com" in link:
            await build_service()
            id = await getIDFromURL(link)
            try:
                meta = getFileMetadata(id)
            except Exception as e:
                err_msg = ""
                if "File not found" in str(e):
                    err_msg = "The file link you provided doesn't exist or you don't have access to it!"
                elif "Failed to retrieve" in str(e):
                    err_msg = "Authorization Error with Google! Make sure you generated token.pickle."
                else:
                    err_msg = f"Error in Google API: {e}"
                logging.error(err_msg)
                await cancelTask(err_msg)
                return # Return to stop further execution on error
            if meta.get("mimeType") == "application/vnd.google-apps.folder":
                Transfer.total_down_size += get_Gfolder_size(id)
            else:
                Transfer.total_down_size += int(meta.get("size", 0))
        elif "t.me" in link:
            media, _ = await media_Identifier(link)
            if media and hasattr(media, 'file_size'):
                Transfer.total_down_size += media.file_size
            else:
                logging.warning("Couldn't get file size from Telegram Message")
        else:
            # We don't calculate size for aria2/ytdl beforehand anymore to prevent errors
            pass


async def get_d_name(link: str):
    if len(BOT.Options.custom_name) != 0:
        Messages.download_name = BOT.Options.custom_name
        return

    try:
        # Check for magnet link first to avoid aria2c dry-run error
        if link.startswith("magnet:"):
            Messages.download_name = "Fetching Torrent Name..."
            return

        if "drive.google.com" in link:
            id = await getIDFromURL(link)
            meta = getFileMetadata(id)
            Messages.download_name = meta["name"]
        elif "t.me" in link:
            media, _ = await media_Identifier(link)
            Messages.download_name = media.file_name if hasattr(media, "file_name") else "Telegram File"
        elif "youtube.com" in link or "youtu.be" in link:
            Messages.download_name = await get_YT_Name(link)
        elif "mega.nz" in link:
            # Mega name is fetched during download process
            Messages.download_name = "Mega.nz Download"
        else:
            # Only use get_Aria2c_Name for normal links, not magnets
            Messages.download_name = get_Aria2c_Name(link)
    except Exception as e:
        logging.error(f"Error getting download name for '{link}': {e}")
        Messages.download_name = "Could not determine name"
