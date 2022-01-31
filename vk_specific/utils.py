import asyncio
import concurrent
import re
import typing
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
from os import getenv
from types import SimpleNamespace
from typing import List, Callable, Union, Optional

from vkbottle import PhotoMessageUploader, DocMessagesUploader
from vkbottle.bot import rules, Message, Blueprint
from vkbottle_types.objects import MessagesForeignMessage, MessagesMessageAttachment, MessagesMessageAttachmentType, \
    PhotosPhotoSizesType, MessagesMessage

from common import utils as common
from vk_specific.base import Base

bp = Blueprint()


class CommandRule(rules.ABCMessageRule):
    def __init__(self, command: List[str]):
        rules.ABCMessageRule.__init__(self)
        self._command = command

    async def check(self, message: Message) -> bool:
        return any(message.text.lower().startswith(x) for x in self._command)


class FromBotAdminRule(rules.ABCMessageRule):
    def __init__(self):
        rules.ABCMessageRule.__init__(self)

    async def check(self, message: Message) -> bool:
        return message.from_id == admin


def get_arguments(text: str) -> str:
    return re.sub(r'^[\S]*\s?', '', text, 1)


async def is_admin(_id: int, peer: int):
    if _id < 0:
        return False
    members = (await bp.api.messages.get_conversation_members(peer)).items
    for member in members:
        if member.member_id == _id and member.is_admin:
            return True
    return False


def command_limit(command: str, interval: int = 1000):
    def decorator(func: Callable):
        async def wrapper(message: Message, *args, **kwargs):
            remaining = await common.chat.rate_limit(f'vk{message.from_id}', interval)
            if remaining > 0:
                return await message.answer(f'Не так быстро! Жди {remaining / 1000} секунд')
            if remaining == -1:
                return
            if await common.chat.get_limit(f'vk{message.chat_id}', command, str(message.from_id)) != 0:
                return await func(message, *args, **kwargs)

        return wrapper

    return decorator


async def get_photo_url(message: Union[Message, MessagesForeignMessage], _all=False) -> Union[str, List[str], None]:
    async def process(attachment: MessagesMessageAttachment) -> str:
        url = None
        if attachment.type == MessagesMessageAttachmentType.PHOTO:
            # If possible get proportional image
            for size in reversed(attachment.photo.sizes):
                if size.type not in (PhotosPhotoSizesType.R, PhotosPhotoSizesType.Q, PhotosPhotoSizesType.P,
                                     PhotosPhotoSizesType.O):
                    url = size.url
                    break
            if not url:
                url = attachment.photo.sizes[-1].url
        return url

    if _all:
        return list(await asyncio.gather(*[process(a) for a in message.attachments if 'photo' in dir(a)]))
    if message.attachments:
        return await process(message.attachments[0])
    else:
        return None


async def unpack_fwd(message: Union[Message, MessagesMessage], photos_max: Optional[Union[int, bool]] = 1) -> \
        typing.Tuple[typing.OrderedDict[int, str], typing.OrderedDict[int, List[str]], typing.OrderedDict[int, int]]:
    fwd = OrderedDict()
    fwd_ids = OrderedDict()
    fwd_msgs = []
    fwd_photos = OrderedDict()
    if photos_max is False:
        photos_max = 100

    async def _unpack_fwd(msgs: List[MessagesForeignMessage]):
        for x in msgs:
            if x and x.conversation_message_id not in fwd_msgs:
                fwd_ids.update({x.conversation_message_id: x.from_id})
                if x.text:
                    fwd.update({x.conversation_message_id: x.text})
                if x.fwd_messages:
                    await _unpack_fwd(x.fwd_messages)
                if x.attachments and (not photos_max or len(fwd_photos) < photos_max):
                    photos = await get_photo_url(x, True)
                    for photo in photos:
                        if len(fwd_photos) == photos_max:
                            break
                        if x.conversation_message_id not in fwd_photos.keys():
                            fwd_photos[x.conversation_message_id] = [photo]
                        else:
                            fwd_photos[x.conversation_message_id].append(photo)
                fwd_msgs.append(x.conversation_message_id)

    await _unpack_fwd([message.reply_message] + message.fwd_messages)
    return fwd, fwd_photos, fwd_ids


def photo_callback(message: Message, _fut: concurrent.futures.Future, _list: bool = False,
                   res_callback: Union[None, typing.Callable[[str], typing.Awaitable]] = None):
    async def _callback(result: Union[bytes, List[bytes]]):
        if _list:
            attachment = ','.join(await asyncio.gather(*[photo_uploader.upload(r) for r in result]))
        else:
            attachment = await photo_uploader.upload(result)
        await message.answer(attachment=attachment)
        if res_callback is not None:
            await res_callback(attachment)

    res = _fut.result()
    asyncio.ensure_future(_callback(res), loop=loop)


pool = ProcessPoolExecutor(max_workers=cpu_count() // 2)
admin = int(getenv('ADMIN'))
commands = SimpleNamespace(start=['/начать', '/start', '/команды', '/commands', '/помощь', '/help'],
                           demotivator=['/демотиватор', '/demotivator'],
                           nouveau=['/nouveau', '/нуво', '/ноувеау'],
                           optimization=['/оптимизация', '/optimization'],
                           objection=['/обжекшон', '/objection'],
                           objection_conf=['/обжекшонконф', '/objectionconf'],
                           zhirinovskysuggested=['/жириновский', '/жирик', '/zhirinovsky'],
                           friday=['/friday', '/пятница'],
                           base=['/base', '/база'],
                           exchange=['/биржа', '/exchange'],
                           cum=['/cum', '/кончил'])
loop = asyncio.new_event_loop()

photo_uploader: PhotoMessageUploader
docs_uploader: DocMessagesUploader
base: Base
