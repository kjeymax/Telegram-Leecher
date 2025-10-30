import logging
import yt_dlp
from asyncio import sleep
from threading import Thread
from os import makedirs, path as ospath
from colab_leecher.utility.handler import cancelTask
from colab_leecher.utility.variables import YTDL, MSG, Messages, Paths, BOT
from colab_leecher.utility.helper import getTime, keyboard, sizeUnit, status_bar, sysINFO


async def YTDL_Status(link, num):
    global Messages, YTDL
    name = await get_YT_Name(link)
    Messages.status_head = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<code>{name}</code>\n"

    YTDL_Thread = Thread(target=YouTubeDL, name="YouTubeDL", args=(link,))
    YTDL_Thread.start()

    while YTDL_Thread.is_alive():  # Until ytdl is downloading
        if YTDL.header:
            sys_text = sysINFO()
            message = YTDL.header
            try:
                await MSG.status_msg.edit_text(text=Messages.task_msg + Messages.status_head + message + sys_text, reply_markup=keyboard())
            except Exception:
                pass
        else:
            try:
                await status_bar(
                    down_msg=Messages.status_head,
                    speed=YTDL.speed,
                    percentage=float(YTDL.percentage),
                    eta=YTDL.eta,
                    done=YTDL.done,
                    left=YTDL.left,
                    engine="H-YTDL 🏮",
                )
            except Exception:
                pass

        await sleep(2.5)


class MyLogger:
    def __init__(self):
        pass

    def debug(self, msg):
        global YTDL, BOT # ⭐️ BOT import කරන්න

        if "item" in str(msg):
            msgs = msg.split(" ")
            YTDL.header = f"\n⏳ __Getting Video Information {msgs[-3]} of {msgs[-1]}__"
        
        # ⭐️ --- "Converting" හෝ "Merging" පණිවිඩය පෙන්වීමට --- ⭐️
        elif "[ExtractAudio]" in str(msg) or "[ffmpeg]" in str(msg):
            # Check if we are in audio-only mode (and not 'original')
            if BOT.Options.audio_format and BOT.Options.audio_format != "original": 
                YTDL.header = f"\n🎵 **Converting to {BOT.Options.audio_format.upper()}...** (Please wait)"
            
            # Check if we are in video mode
            elif not BOT.Options.audio_format:
                YTDL.header = "\n📥 **Merging Fragments...** (This may take a moment)"
        # ⭐️ --- වෙනස් කිරීම අවසන් --- ⭐️


    @staticmethod
    def warning(msg):
        pass

    @staticmethod
    def error(msg):
        # if msg != "ERROR: Cancelling...":
        # print(msg)
        pass


# ⭐️ 
def YouTubeDL(url):
    global YTDL, BOT, Paths # ⭐️ Paths මෙහි import කරන්න (අත්‍යවශ්‍යයි)

    def my_hook(d):
        global YTDL

        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes", 0)  # Use 0 as default if total_bytes is None
            dl_bytes = d.get("downloaded_bytes", 0)
            percent = d.get("downloaded_percent", 0)
            speed = d.get("speed", "N/A")
            eta = d.get("eta", 0)

            if total_bytes:
                percent = round((float(dl_bytes) * 100 / float(total_bytes)), 2)

            YTDL.header = "" # Clear merging/converting message
            YTDL.speed = sizeUnit(speed) if speed else "N/A"
            YTDL.percentage = percent
            YTDL.eta = getTime(eta) if eta else "N/A"
            YTDL.done = sizeUnit(dl_bytes) if dl_bytes else "N/A"
            YTDL.left = sizeUnit(total_bytes) if total_bytes else "N/A"
        
        elif d["status"] == "finished":
            if not BOT.Options.audio_format: # Video mode
                YTDL.header = "\n📥 **Merging Fragments...** (This may take a moment)"
            elif BOT.Options.audio_format and BOT.Options.audio_format != "original": # Audio convert mode
                YTDL.header = f"\n🎵 **Converting to {BOT.Options.audio_format.upper()}...** (Please wait)"
            # 'original' audio වලදී කිසිවක් පෙන්වීම අවශ්‍ය නැත.

        elif d["status"] == "downloading fragment":
            pass
        else:
            logging.info(d)

    # -----------------------------------------------------
    # ⭐️ --- YTDL Options සඳහා නව Logic --- ⭐️
    # -----------------------------------------------------
    
    # 1. මූලික සැකසුම් (Common settings)
    ydl_opts = {
        "writethumbnail": True,
        "concurrent_fragment_downloads": 4,
        "overwrites": True,
        "progress_hooks": [my_hook],
        "writesubtitles": "true",
        "subtitleslangs": ["all"],
        "extractor_args": {"subtitlesformat": "srt"},
        "logger": MyLogger(),
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }
    
    # ⭐️ --- COOKIE LOGIC (Cookie ගොනුව තිබේ නම් එය එක් කිරීම) --- ⭐️
    if ospath.exists(Paths.COOKIES_PATH):
        logging.info("YouTube Cookies file found. Using cookies...")
        ydl_opts["cookiefile"] = Paths.COOKIES_PATH
    else:
        logging.warning("YouTube Cookies file not found. High-quality downloads may fail.")
    # ⭐️ --- END COOKIE LOGIC --- ⭐️


    audio_format = BOT.Options.audio_format
    
    if audio_format == "mp3" or audio_format == "wav":
        # --- Audio-Only (Convert) Settings ---
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["merge_output_format"] = None
        ydl_opts["postprocessors"] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format, # mp3 or wav
            'preferredquality': '192', # mp3 quality
        }]
    
    elif audio_format == "original":
        # --- Audio-Only (Original) Settings ---
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["merge_output_format"] = None # No merge/convert
    
    else:
        # --- Video Settings (default) ---
        ydl_opts["format"] = BOT.Options.ytdl_format # 1080p or 4K
        ydl_opts["merge_output_format"] = "mp4"

    # ⭐️ --- නව Logic අවසානය --- ⭐️


    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if not ospath.exists(Paths.thumbnail_ytdl):
            makedirs(Paths.thumbnail_ytdl)
        try:
            info_dict = ydl.extract_info(url, download=False)
            YTDL.header = "⌛ __Please WAIT a bit...__"
            
            # --- Output Template (outtmpl) Logic ---
            def get_output_template(base_path):
                if audio_format == "mp3" or audio_format == "wav":
                    return f"{base_path}.{audio_format}"
                elif audio_format == "original":
                     # We don't know the extension yet, so let yt-dlp decide
                    return f"{base_path}.%(ext)s"
                else: # Video
                    return f"{base_path}.%(ext)s"

            if "_type" in info_dict and info_dict["_type"] == "playlist":
                playlist_name = info_dict["title"] 
                playlist_path = ospath.join(Paths.down_path, playlist_name)
                if not ospath.exists(playlist_path):
                    makedirs(playlist_path)
                
                # ⭐️ --- BUG FIX: `ydl.params` ලෙස වෙනස් කරන ලදී --- ⭐️
                ydl.params['outtmpl'] = {
                    "default": get_output_template(f"{playlist_path}/%(title)s"),
                    "thumbnail": f"{Paths.thumbnail_ytdl}/%(id)s.%(ext)s",
                }
                for entry in info_dict["entries"]:
                    video_url = entry["webpage_url"]
                    try:
                        ydl.download([video_url])
                    except yt_dlp.utils.DownloadError as e:
                        if e.exc_info[0] == 36: # Filename too long
                            # ⭐️ --- BUG FIX: `ydl.params` ලෙස වෙනස් කරන ලදී --- ⭐️
                            ydl.params['outtmpl']["default"] = get_output_template(f"{playlist_path}/%(id)s")
                            ydl.download([video_url])
            else:
                YTDL.header = ""
                # ⭐️ --- BUG FIX: `ydl.params` ලෙස වෙනස් කරන ලදී --- ⭐️
                ydl.params['outtmpl'] = {
                    "default": get_output_template(f"{Paths.down_path}/%(title)s"),
                    "thumbnail": f"{Paths.thumbnail_ytdl}/%(id)s.%(ext)s",
                }
                try:
                    ydl.download([url])
                except yt_dlp.utils.DownloadError as e:
                    if e.exc_info[0] == 36: # Filename too long
                        # ⭐️ --- BUG FIX: `ydl.params` ලෙස වෙනස් කරන ලදී --- ⭐️
                        ydl.params['outtmpl']["default"] = get_output_template(f"{Paths.down_path}/%(id)s")
                        ydl.download([url])
        except Exception as e:
            logging.error(f"YTDL ERROR: {e}")


async def get_YT_Name(link):
    # දෝෂයක් (error) ආවිට task එක cancel නොකර, error එක log කර ඉදිරියට යයි
    with yt_dlp.YoutubeDL({"logger": MyLogger()}) as ydl:
        try:
            info = ydl.extract_info(link, download=False)
            if "title" in info and info["title"]: 
                return info["title"]
            else:
                return "UNKNOWN DOWNLOAD NAME"
        except Exception as e:
            logging.error(f"Can't get YTDL name for {link}. Error: {str(e)}")
            # await cancelTask(f"Can't Download from this link. Because: {str(e)}") # ⭐️ Cancel ඉවත් කරන ලදී
            return "UNKNOWN OR UNAVAILABLE VIDEO" # ⭐️ නව return අගය
