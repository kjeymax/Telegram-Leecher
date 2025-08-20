import logging
from datetime import datetime
from os import path as ospath
from colab_leecher import colab_bot
from colab_leecher.utility.handler import cancelTask
from colab_leecher.utility.variables import Transfer, Paths, Messages, BotTimes
from colab_leecher.utility.helper import speedETA, getTime, sizeUnit, status_bar


async def media_Identifier(link):
    parts = link.split("/")
    message_id, message = parts[-1], None
    msg_chat_id = "-100" + parts[4]
    message_id, msg_chat_id = int(message_id), int(msg_chat_id)
    try:
        message = await colab_bot.get_messages(msg_chat_id, message_id)
    except Exception as e:
        logging.error(f"Error getting messages from Telegram: {e}")
        return None, None  # Return None if message retrieval fails

    if message is None:
        logging.error("Message not found or couldn't be retrieved from Telegram")
        return None, None  # Return None if message is not found or None
    
    media = (
        message.document
        or message.photo
        or message.video
        or message.audio
        or message.voice
        or message.video_note
        or message.sticker
        or message.animation
        or None
    )
    if media is None:
        logging.error("No media found in the Telegram message")
        return None, None  # Return None if no media is found in the message
    return media, message


async def download_progress(current, total):
    speed_string, eta, percentage = speedETA(start_time, current, total)

    await status_bar(
        down_msg=Messages.status_head,
        speed=speed_string,
        percentage=percentage,
        eta=getTime(eta),
        done=sizeUnit(sum(Transfer.down_bytes) + current),
        left=sizeUnit(Transfer.total_down_size),
        engine="Pyrogram 💥",
    )


async def TelegramDownload(link, num):
    global start_time, TRANSFER_INFO
    media, message = await media_Identifier(link)
    if media is not None:
        name = media.file_name if hasattr(media, "file_name") else "None"
    else:
        logging.error("Couldn't Download Telegram Message")
        await cancelTask("Couldn't Download Telegram Message")
        return

    Messages.status_head = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<code>{name}</code>\n"
    start_time = datetime.now()
    file_path = ospath.join(Paths.down_path, name)
    
    await message.download(progress=download_progress, in_memory=False, file_name=file_path)
    Transfer.down_bytes.append(media.file_size)
