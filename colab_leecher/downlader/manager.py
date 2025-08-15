import logging
from natsort import natsorted
from datetime import datetime
from asyncio import sleep
from colab_leecher.downlader.mega import megadl
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from colab_leecher.utility.handler import cancelTask
from colab_leecher.downlader.ytdl import YTDL_Status, get_YT_Name
from colab_leecher.downlader.libtorrent import qbittorrent_Download, get_qbittorrent_Name
from colab_leecher.utility.helper import isYtdlComplete, keyboard, sysINFO
from colab_leecher.downlader.telegram import TelegramDownload, media_Identifier
from colab_leecher.utility.variables import BOT, Transfer, MSG, Messages, Libtorrent, BotTimes
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
                    executor = ProcessPoolExecutor()
                    await megadl(link, i + 1)
                else:
                    libtorrent_dn = f"<b>PLEASE WAIT ⌛</b>\n\n__Getting Download Info For__\n\n<code>{link}</code>"
                    try:
                        await MSG.status_msg.edit_text(
                            text=libtorrent_dn + sysINFO(), reply_markup=keyboard()
                        )
                    except Exception as e:
                        logging.error(f"Error updating message: {e}")
                    Libtorrent.link_info = False
                    await libtorrent_Download(link, i + 1)
            except Exception as Error:
                await cancelTask(f"Download Error: {str(Error)}")
                logging.error(f"Error While Downloading: {Error}")
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
            else:
                if meta.get("mimeType") == "application/vnd.google-apps.folder":
                    Transfer.total_down_size += get_Gfolder_size(id)
                else:
                    Transfer.total_down_size += int(meta["size"])
        elif "t.me" in link:
            media, _ = await media_Identifier(link)
            if media is not None:
                size = media.file_size
                Transfer.total_down_size += size
            else:
                logging.error("Couldn't Download Telegram Message")
        else:
            pass


async def get_d_name(link: str):
    if len(BOT.Options.custom_name) != 0:
        Messages.download_name = BOT.Options.custom_name
        return
    if "drive.google.com" in link:
        id = await getIDFromURL(link)
        meta = getFileMetadata(id)
        Messages.download_name = meta["name"]
    elif "t.me" in link:
        media, _ = await media_Identifier(link)
        Messages.download_name = media.file_name if hasattr(media, "file_name") else "None"
    elif "youtube.com" in link or "youtu.be" in link:
        Messages.download_name = await get_YT_Name(link)
    elif "mega.nz" in link:
        Messages.download_name = "Don't Know 🤷‍♂️ (Trying)"
    else:
        Messages.download_name = get_qbittorrent_Name(link)
