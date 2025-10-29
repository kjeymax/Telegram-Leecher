# copyright 2023 © Xron Trix | https://github.com/Xrontrix10
# copyright 2023 © Kavindu AJ | https://github.com/kjeymax/Telegram-Leecher


import pytz
import shutil
import logging
from time import time
from datetime import datetime
from os import makedirs, path as ospath, system
from colab_leecher.downlader import ytdl
from colab_leecher import OWNER, colab_bot, DUMP_ID
from colab_leecher.downlader.manager import calDownSize, get_d_name, downloadManager
from colab_leecher.utility.helper import getSize, applyCustomName, keyboard, sysINFO
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from colab_leecher import OWNER
from colab_leecher.utility.handler import (
    Leech,
    Unzip_Handler,
    Zip_Handler,
    SendLogs,
    cancelTask,
)
from colab_leecher.utility.variables import (
    BOT,
    MSG,
    BotTimes,
    Messages,
    Paths,
    Transfer,
    TaskError,
    Aria2c,  # Add Aria2c import
)


async def taskScheduler():
    global BOT, MSG, BotTimes, Messages, Paths, Transfer, TaskError
    src_text = []
    is_dualzip, is_unzip, is_zip, is_dir = (
        BOT.Mode.type == "undzip",
        BOT.Mode.type == "unzip",
        BOT.Mode.type == "zip",
        BOT.Mode.mode == "dir-leech",
    )
    # Reset Texts
    Messages.download_name = ""
    Messages.task_msg = f"<b>🦞 TASK MODE » </b>"
    Messages.dump_task = (
        Messages.task_msg
        + f"<i>{BOT.Mode.type.capitalize()} {BOT.Mode.mode.capitalize()} as {BOT.Setting.stream_upload}</i>\n\n<b>🖇️ SOURCES » </b>"
    )
    Transfer.sent_file = []
    Transfer.sent_file_names = []
    Transfer.down_bytes = [0, 0]
    Transfer.up_bytes = [0, 0]
    Messages.download_name = ""
    Messages.task_msg = ""
    Messages.status_head = f"<b>📥 DOWNLOADING » </b>\n"

    if is_dir:
        if not ospath.exists(BOT.SOURCE[0]):
            TaskError.state = True
            TaskError.text = "Task Failed. Because: Provided Directory Path Not Exists"
            logging.error(TaskError.text)
            return
        if not ospath.exists(Paths.temp_dirleech_path):
            makedirs(Paths.temp_dirleech_path)
        Messages.dump_task += f"\n\n📂 <code>{BOT.SOURCE[0]}</code>"
        Transfer.total_down_size = getSize(BOT.SOURCE[0])
        Messages.download_name = ospath.basename(BOT.SOURCE[0])
    else:
        for link in BOT.SOURCE:
            if "t.me" in link:
                ida = "💬"
            elif "drive.google.com" in link:
                ida = "♻️"
            elif "magnet" in link or "torrent" in link:
                ida = "🧲"
                Messages.caution_msg = "\n\n⚠️<i><b> Torrents Are Strictly Prohibited in Google Colab</b>, Try to avoid Magnets !</i>"
            elif "youtube.com" in link or "youtu.be" in link:
                ida = "🏮"
            else:
                ida = "🔗"
            code_link = f"\n\n{ida} <code>{link}</code>"
            if len(Messages.dump_task + code_link) >= 4096:
                src_text.append(Messages.dump_task)
                Messages.dump_task = code_link
            else:
                Messages.dump_task += code_link
                
    # Get the current date and time in the specified time zone
    cdt = datetime.now(pytz.timezone("Asia/Kolkata"))
    dt = cdt.strftime(" %d-%m-%Y")
    Messages.dump_task += f"\n\n<b>📆 Task Date » </b><i>{dt}</i>"

    src_text.append(Messages.dump_task)

    if ospath.exists(Paths.WORK_PATH):
        shutil.rmtree(Paths.WORK_PATH)
        # makedirs(Paths.WORK_PATH)
        makedirs(Paths.down_path)
    else:
        makedirs(Paths.WORK_PATH)
        makedirs(Paths.down_path)
    Messages.link_p = str(DUMP_ID)[4:]

    try:
        system(f"aria2c -d {Paths.WORK_PATH} -o Hero.jpg https://picsum.photos/900/600")
    except Exception:
        Paths.HERO_IMAGE = Paths.DEFAULT_HERO

    MSG.sent_msg = await colab_bot.send_message(chat_id=DUMP_ID, text=src_text[0])

    if len(src_text) > 1:
        for lin in range(1, len(src_text)):
            MSG.sent_msg = await MSG.sent_msg.reply_text(text=src_text[lin], quote=True)

    Messages.src_link = f"https://t.me/c/{Messages.link_p}/{MSG.sent_msg.id}"
    Messages.task_msg += f"__[{BOT.Mode.type.capitalize()} {BOT.Mode.mode.capitalize()} as {BOT.Setting.stream_upload}]({Messages.src_link})__\n\n"

    await MSG.status_msg.delete()
    img = Paths.THMB_PATH if ospath.exists(Paths.THMB_PATH) else Paths.HERO_IMAGE
    MSG.status_msg = await colab_bot.send_photo(  # type: ignore
        chat_id=OWNER,
        photo=img,
        caption=Messages.task_msg
        + Messages.status_head
        + f"\n📝 __Starting DOWNLOAD...__"
        + sysINFO(),
        reply_markup=keyboard(),
    )

    await calDownSize(BOT.SOURCE)

    if not is_dir:
        await get_d_name(BOT.SOURCE[0])
    else:
        Messages.download_name = ospath.basename(BOT.SOURCE[0])

    if is_zip:
        Paths.down_path = ospath.join(Paths.down_path, Messages.download_name)
        if not ospath.exists(Paths.down_path):
            makedirs(Paths.down_path)

    BotTimes.current_time = time()

    if BOT.Mode.mode != "mirror":
        await Do_Leech(BOT.SOURCE, is_dir, BOT.Mode.ytdl, is_zip, is_unzip, is_dualzip)
    else:
        await Do_Mirror(BOT.SOURCE, BOT.Mode.ytdl, is_zip, is_unzip, is_dualzip)


async def Do_Leech(source, is_dir, is_ytdl, is_zip, is_unzip, is_dualzip):
    final_path = ""
    is_folder = True

    if is_dir:
        # For Dir-Leech, we process the folder and then ask for options
        source_path = source[0]
        if not ospath.exists(source_path):
            logging.error("Provided directory does not exist!")
            await cancelTask("Provided directory does not exist!")
            return

        if is_zip:
            await Zip_Handler(source_path, True, False)
            final_path = Paths.temp_zpath
        elif is_unzip:
            await Unzip_Handler(source_path, False)
            final_path = Paths.temp_unzip_path
        elif is_dualzip:
            await Unzip_Handler(source_path, False)
            await Zip_Handler(Paths.temp_unzip_path, True, True)
            final_path = Paths.temp_zpath
        else: # Normal Dir-Leech
            final_path = source_path
            is_folder = ospath.isdir(source_path)

    else: # For Normal Leech (from links)
        await downloadManager(source, is_ytdl)
        Transfer.total_down_size = getSize(Paths.down_path)
        applyCustomName() # Renaming files

        if is_zip:
            await Zip_Handler(Paths.down_path, True, True)
            final_path = Paths.temp_zpath
        elif is_unzip:
            await Unzip_Handler(Paths.down_path, True)
            final_path = Paths.temp_unzip_path
        elif is_dualzip:
            await Unzip_Handler(Paths.down_path, True)
            await Zip_Handler(Paths.temp_unzip_path, True, True)
            final_path = Paths.temp_zpath
        else: # Normal Leech
            final_path = Paths.down_path
            is_folder = True
    
    # ⭐️ --- NEW POST-PROCESSING LOGIC --- ⭐️
    # Check if the final path contains video files to offer processing options
    
    # Simple check: Let's assume for now if it's not a zip/unzip task, we can process it.
    # A more advanced check would loop through files in final_path.
    is_media_task = not (is_zip or is_unzip or is_dualzip)
    
    if final_path and is_media_task:
        # Store the final path and type in a global variable to access it later
        BOT.Options.final_leech_path = final_path
        BOT.Options.is_leech_folder = is_folder

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Change Metadata", callback_data="post_process_meta")],
            [InlineKeyboardButton("📖 Extract Subtitles", callback_data="post_process_subs")],
            [InlineKeyboardButton("🚀 Upload As Is", callback_data="post_process_upload")]
        ])

        try:
            # We need to delete the old status message and send a new one
            await MSG.status_msg.delete()
            MSG.status_msg = await colab_bot.send_message(
                chat_id=OWNER,
                text="✅ **Download/Processing Complete!**\n\nWhat would you like to do with the files?",
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Could not send post-processing options: {e}")
            # If we can't send options, just upload directly
            await Leech(final_path, is_folder)
            await SendLogs(True)
    
    elif final_path: # If it's a zip/unzip task, just upload
        await Leech(final_path, is_folder)
        await SendLogs(True)
    
    else:
        await cancelTask("Failed to determine final path for leeching.")


async def Do_Mirror(source, is_ytdl, is_zip, is_unzip, is_dualzip):
    if not ospath.exists(Paths.MOUNTED_DRIVE):
        await cancelTask(
            "Google Drive is NOT MOUNTED ! Stop the Bot and Run the Google Drive Cell to Mount, then Try again !"
        )
        return

    if not ospath.exists(Paths.mirror_dir):
        makedirs(Paths.mirror_dir)

    await downloadManager(source, is_ytdl)

    Transfer.total_down_size = getSize(Paths.down_path)

    applyCustomName()

    cdt = datetime.now()
    cdt_ = cdt.strftime("Uploaded » %Y-%m-%d %H:%M:%S")
    mirror_dir_ = ospath.join(Paths.mirror_dir, cdt_)

    if is_zip:
        await Zip_Handler(Paths.down_path, True, True)
        shutil.copytree(Paths.temp_zpath, mirror_dir_)
    elif is_unzip:
        await Unzip_Handler(Paths.down_path, True)
        shutil.copytree(Paths.temp_unzip_path, mirror_dir_)
    elif is_dualzip:
        await Unzip_Handler(Paths.down_path, True)
        await Zip_Handler(Paths.temp_unzip_path, True, True)
        shutil.copytree(Paths.temp_zpath, mirror_dir_)
    else:
        shutil.copytree(Paths.down_path, mirror_dir_)

    await SendLogs(False)
