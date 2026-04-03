import asyncio
import os
import re
import aiohttp
import json
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from ANIYAXMUSIC.utils.database import is_on_off
from ANIYAXMUSIC.utils.formatters import time_to_seconds

# ─────────────────────────────
# 🔥 SHRUTI API CONFIG
# ─────────────────────────────
FALLBACK_API_URL = "https://shrutibots.site"
YOUR_API_URL = None

cookies_file = "ANIYAXMUSIC/assets/cookies.txt"

# 🔄 API URL Loader (Dynamic)
async def get_api_url():
    global YOUR_API_URL
    if YOUR_API_URL: return YOUR_API_URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pastebin.com/raw/rLsBhAQa", timeout=5) as resp:
                if resp.status == 200:
                    YOUR_API_URL = (await resp.text()).strip()
                else:
                    YOUR_API_URL = FALLBACK_API_URL
    except:
        YOUR_API_URL = FALLBACK_API_URL
    return YOUR_API_URL

# 📥 Direct Downloader Function
async def download_via_shruti(link: str, is_video: bool = False):
    api_url = await get_api_url()
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    
    # Folder Setup
    folder = "downloads"
    if not os.path.exists(folder): os.makedirs(folder)
    
    ext = "mp4" if is_video else "mp3"
    file_path = os.path.join(folder, f"{video_id}.{ext}")

    # Cache Check
    if os.path.exists(file_path):
        return file_path

    try:
        async with aiohttp.ClientSession() as session:
            req_type = "video" if is_video else "audio"
            
            # Step 1: Get Token
            async with session.get(f"{api_url}/download", params={"url": video_id, "type": req_type}, timeout=20) as resp:
                if resp.status != 200: return None
                data = await resp.json()
                token = data.get("download_token")
                if not token: return None

            # Step 2: Stream & Save
            stream_url = f"{api_url}/stream/{video_id}?type={req_type}"
            async with session.get(stream_url, headers={"X-Download-Token": token}, timeout=600) as resp:
                if resp.status != 200: return None
                
                with open(file_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(16384):
                        f.write(chunk)
                
                return file_path if os.path.exists(file_path) else None
    except Exception as e:
        print(f"❌ API Download Error: {e}")
        return None

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        if re.search(self.regex, link): return True
        return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset: break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,): return None
        return text[offset : offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        if "&" in link: link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            if str(duration_min) == "None": duration_sec = 0
            else: duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        if "&" in link: link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]: return result["title"]

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        if "&" in link: link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]: return result["duration"]

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        if "&" in link: link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]: return result["thumbnails"][0]["url"].split("?")[0]

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid: link = self.listbase + link
        if "&" in link: link = link.split("&")[0]
        playlist = await shell_cmd(
            f"yt-dlp --cookies {cookies_file} -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = playlist.split("\n")
            result = [key for key in result if key]
        except: result = []
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        if "&" in link: link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title, "link": yturl, "vidid": vidid,
            "duration_min": duration_min, "thumb": thumbnail
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        if "&" in link: link = link.split("&")[0]
        ytdl_opts = {"quiet": True, "cookiefile": cookies_file}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    if "dash" not in str(format["format"]).lower():
                        formats_available.append({
                            "format": format["format"], "filesize": format.get("filesize"),
                            "format_id": format["format_id"], "ext": format["ext"],
                            "format_note": format["format_note"], "yturl": link
                        })
                except: continue
        return formats_available, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        if "&" in link: link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    # ─────────────────────────────────────────────
    # 🔥 MODIFIED DOWNLOAD (USES SHRUTI API DIRECTLY)
    # ─────────────────────────────────────────────
    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid: link = self.base + link

        # 1️⃣ API Download Attempt
        is_video_req = True if video or songvideo else False
        
        try:
            downloaded_file = await download_via_shruti(link, is_video=is_video_req)
            if downloaded_file:
                return downloaded_file, True  # Success
        except Exception as e:
            print(f"API Failed, trying Fallback: {e}")

        # 2️⃣ Fallback (YT-DLP) - Agar API fail ho jaye tabhi chalega
        # Render par ye fail hi hoga, but safety ke liye rakha hai.
        loop = asyncio.get_running_loop()

        def audio_dl():
            ydl_optssx = {
                "format": "bestaudio/best", "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True, "nocheckcertificate": True, "quiet": True,
                "no_warnings": True, "cookiefile": cookies_file,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz): return xyz
            x.download([link])
            return xyz

        def video_dl():
            ydl_optssx = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True, "nocheckcertificate": True, "quiet": True,
                "no_warnings": True, "cookiefile": cookies_file,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz): return xyz
            x.download([link])
            return xyz

        if video:
            direct = True
            downloaded_file = await loop.run_in_executor(None, video_dl)
        else:
            direct = True
            downloaded_file = await loop.run_in_executor(None, audio_dl)
            
        return downloaded_file, direct
                
